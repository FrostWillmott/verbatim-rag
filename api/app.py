"""
Clean FastAPI server for the Verbatim RAG system.
Decoupled from RAG logic with proper dependency injection.
"""

import logging
import os
import re
import sys
from contextlib import asynccontextmanager
from typing import Annotated, Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

try:
    from verbatim_rag import (
        QueryResponse,
        TemplateManager,
        VerbatimRAG,
    )
    from verbatim_rag.extractors import SpanExtractionUnavailable
except ImportError as e:
    print(f"Error importing verbatim_rag: {e}")
    sys.exit(1)

from api.config import APIConfig, get_config
from api.dependencies import (
    check_system_ready,
    get_api_service,
    get_rag_instance,
    get_template_manager,
)
from api.services.rag_service import APIService

logger = logging.getLogger(__name__)


def _extraction_unavailable(exc: Exception) -> HTTPException:
    """503 for "the model could not be asked", which is not "the corpus has nothing".

    The provider's own message is passed through rather than swallowed: it names
    the cause — an unusable key, a model this account cannot reach — and the
    alternative is what these routes used to answer, which was a confident
    "no relevant information found in the provided documents" with a 200.
    """
    logger.error("Span extraction unavailable: %s", exc)
    return HTTPException(status_code=503, detail=f"Span extraction is unavailable: {exc}")


def llm_key_is_configured() -> bool:
    """Whether a usable LLM key is present.

    An empty value counts as missing: .env.example ships `OPENAI_API_KEY=` and
    LLMClient falls back to a placeholder, so a blank key produces the same
    failure as an absent one — only later, on the first query.
    """
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def count_indexed_documents(rag: VerbatimRAG) -> int | None:
    """How many documents the index holds, or None if the store cannot say.

    Deliberately the same call `/api/documents` already serves its listing from,
    rather than a second counting mechanism. That inherits the listing's limit,
    so the number saturates instead of growing without bound — enough to tell an
    empty index from a populated one, which is what the status is asked for.

    It also inherits the listing's blind spot: the Milvus store catches its own
    failures and returns an empty list, so a store that is broken reports the
    same zero as a store that is empty. None is returned only for the case this
    function can see — a store with no such method at all.
    """
    store = getattr(getattr(rag, "index", None), "vector_store", None)
    if not hasattr(store, "get_all_documents"):
        return None
    return len(store.get_all_documents() or [])


# Bounds on what a single request may cost. Without them one caller could ask for
# unbounded retrieval or hand over an arbitrarily large context: before these
# caps, 10 000 context items kept the transform endpoint busy for 41 seconds.
MAX_RETRIEVED_DOCS = 50
MAX_CONTEXT_ITEMS = 100
MAX_CONTEXT_ITEM_CHARS = 100_000


# `filter` is handed to a Milvus expression parser. The library keeps taking a
# free string — that is its public API and not this fork's to redesign — but the
# HTTP surface, which the README calls a prototype, narrows it to the shape the
# vector store actually promotes for filtering. Anything else is refused here
# rather than interpreted downstream.
FILTER_FIELDS = ("user_id", "dataset_id", "document_id")
MAX_FILTER_TERMS = 4
_FILTER_TERM = re.compile(
    r"^(?:%s)\s*==\s*(?P<q>['\"])(?P<value>[^'\"\\]{1,128})(?P=q)$" % "|".join(FILTER_FIELDS)
)


def validate_filter_expression(expression: Optional[str]) -> Optional[str]:
    """Accept only `field == 'value'`, optionally joined by `and`."""
    if expression is None:
        return None

    terms = [term.strip() for term in re.split(r"\s+and\s+", expression.strip(), flags=re.I)]
    if not 1 <= len(terms) <= MAX_FILTER_TERMS:
        raise ValueError(f"filter accepts 1 to {MAX_FILTER_TERMS} terms joined by 'and'")
    for term in terms:
        if not _FILTER_TERM.match(term):
            raise ValueError(
                "each filter term must be <field> == '<value>' with field one of "
                + ", ".join(FILTER_FIELDS)
            )
    # The rebuilt expression, not the one that came in: the split above accepts
    # `AND` and `And`, and Milvus only parses lowercase `and`. Returning the
    # original let a validated filter fail inside pymilvus and surface as a
    # generic 500 instead of the 400 this validator exists to produce.
    return " and ".join(terms)


# Request/Response models
class QueryRequestModel(BaseModel):
    # extra="forbid" so an unsupported parameter is refused instead of silently
    # dropped. `template_id` used to be declared here and reached no consumer at
    # all — neither VerbatimRAG.query nor query_async has such a parameter — so a
    # client could select a template and get an unchanged answer with a 200.
    model_config = ConfigDict(extra="forbid")

    question: str
    k: Optional[int] = Field(default=None, ge=1, le=MAX_RETRIEVED_DOCS)
    hybrid_weights: Optional[dict[str, float]] = None
    rrf_k: int = 60
    filter: Optional[str] = None
    search_params: Optional[dict[str, Any]] = None

    _check_filter = field_validator("filter")(validate_filter_expression)


class StreamQueryRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    num_docs: int = Field(default=5, ge=1, le=MAX_RETRIEVED_DOCS)
    hybrid_weights: Optional[dict[str, float]] = None
    rrf_k: int = 60
    filter: Optional[str] = None
    search_params: Optional[dict[str, Any]] = None

    _check_filter = field_validator("filter")(validate_filter_expression)


class StatusResponse(BaseModel):
    resources_loaded: bool
    message: str
    llm_configured: bool = True
    # None means the store could not be asked, which is not the same as zero.
    document_count: int | None = None


class TemplateListResponse(BaseModel):
    templates: list[dict]


# RAG-agnostic verbatim transform models
class VerbatimContextItem(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_CONTEXT_ITEM_CHARS)
    title: str | None = ""
    source: str | None = ""
    metadata: dict | None = None


class VerbatimTransformRequest(BaseModel):
    # Forbidden at the top level, but deliberately not on VerbatimContextItem:
    # this endpoint accepts context from any RAG, and those items legitimately
    # carry keys we do not know about.
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    context: list[VerbatimContextItem] = Field(default_factory=list, max_length=MAX_CONTEXT_ITEMS)
    answer: str | None = None  # ignored for now


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Verbatim RAG API server...")

    # Dependencies will be initialized on first request
    # No global state initialization needed

    yield

    logger.info("Shutting down Verbatim RAG API server...")


def create_app() -> FastAPI:
    """Create FastAPI application with proper configuration"""
    config = get_config()

    # force=True because this may run after logging is already configured; without
    # it basicConfig is a no-op and LOG_LEVEL would go on being ignored.
    logging.basicConfig(level=config.log_level.upper(), force=True)

    if not llm_key_is_configured():
        logger.warning(
            "OPENAI_API_KEY is unset or empty. The stack still starts, by design, "
            "but every query will fail on the first LLM call. /api/status reports "
            "this as llm_configured=false."
        )

    app = FastAPI(
        title="Verbatim RAG API",
        description="API for provenance-first RAG with source excerpts and citations",
        version="1.0.0",
        lifespan=lifespan,
        debug=config.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=config.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()


# Root endpoint removed to allow static files to serve React app at /


@app.get("/api/documents")
async def get_documents(
    rag: Annotated[VerbatimRAG, Depends(get_rag_instance)],
    _: Annotated[bool, Depends(check_system_ready)],
):
    """
    Get list of indexed documents

    Returns:
        List of documents with metadata
    """
    try:
        # Get documents from the vector store via the index
        if hasattr(rag, "index") and rag.index is not None:
            documents = []

            # Try to get documents from the vector store if it has the method
            if hasattr(rag.index.vector_store, "get_all_documents"):
                docs = rag.index.vector_store.get_all_documents()
                for doc in docs or []:
                    # None, not 0: VerbatimIndex stores documents with an empty
                    # raw_content (index.py has the TODO), so len() here reported
                    # a confident zero for every document ever indexed. A length
                    # that cannot be computed is not a length of zero — the same
                    # distinction /api/status makes for document_count.
                    raw_content = doc.get("raw_content") or ""
                    documents.append(
                        {
                            "id": doc.get("id", "unknown"),
                            "title": doc.get("title", "Unknown Document"),
                            "source": doc.get("source", "Unknown source"),
                            "content_length": len(raw_content) if raw_content else None,
                        }
                    )
            else:
                # Fallback: return a message indicating documents are indexed but not retrievable
                logger.info("Documents are indexed but document metadata retrieval not implemented")

            return {"documents": documents}
        else:
            return {"documents": []}

    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve documents")


@app.get("/api/status", response_model=StatusResponse)
async def get_status(
    config: Annotated[APIConfig, Depends(get_config)],
    rag: Annotated[VerbatimRAG, Depends(get_rag_instance)],
):
    """Get system status"""
    try:
        # `ready` has only ever meant "an index object exists". It cannot tell a
        # working system from an empty one, and the UI renders it as a green
        # "Ready" while every question answers "no relevant information found".
        # The count is what separates the two cases.
        ready = hasattr(rag, "index") and rag.index is not None
        document_count = count_indexed_documents(rag) if ready else None

        if not ready:
            message = "RAG system initializing"
        elif document_count == 0:
            message = "RAG system ready, but no documents are indexed"
        else:
            message = "RAG system ready"

        return StatusResponse(
            resources_loaded=ready,
            message=message,
            llm_configured=llm_key_is_configured(),
            document_count=document_count,
        )
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return StatusResponse(
            resources_loaded=False,
            message=f"System error: {str(e)}",
            llm_configured=llm_key_is_configured(),
        )


@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequestModel,
    api_service: Annotated[APIService, Depends(get_api_service)],
    _: Annotated[bool, Depends(check_system_ready)],
):
    """
    Query the RAG system

    Args:
        request: Query request with question and optional template ID

    Returns:
        Query response with answer and supporting documents
    """
    try:
        # Validate request
        api_service.validate_query_request(request.question)

        # Through the service layer, not past it: DEAD-4 asked whether this
        # class owns the request path, and the answer this fork gives is yes.
        # The bypass is also how BEY-1 stayed hidden — a signature nothing
        # called cannot be seen to be wrong.
        response = api_service.query(
            request.question,
            k=request.k,
            hybrid_weights=request.hybrid_weights,
            rrf_k=request.rrf_k,
            filter=request.filter,
            search_params=request.search_params,
        )

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SpanExtractionUnavailable as e:
        raise _extraction_unavailable(e)
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Query failed")


# deprecated=True, not a removal: /api/query/async has served the same behaviour
# since 2025-07 and this name arrived in 2025-09, so the newer duplicate is the
# one to mark. The flag reaches the OpenAPI schema and nothing else — no caller
# breaks, and the maintainer can move the mark to the other route with one word
# if the answer to DEAD-4 is that the service layer should own the request path.
# See BEY-2 in AUDIT.md.
@app.post("/api/query_async", response_model=QueryResponse, deprecated=True)
async def query_async_endpoint(
    request: QueryRequestModel,
    api_service: Annotated[APIService, Depends(get_api_service)],
    _: Annotated[bool, Depends(check_system_ready)],
):
    """Async query endpoint using async RAG pipeline."""
    try:
        api_service.validate_query_request(request.question)
        response = await api_service.query_async(
            request.question,
            k=request.k,
            hybrid_weights=request.hybrid_weights,
            rrf_k=request.rrf_k,
            filter=request.filter,
            search_params=request.search_params,
        )
        return response
    except SpanExtractionUnavailable as e:
        raise _extraction_unavailable(e)
    except Exception as e:
        logger.error(f"Async query failed: {e}")
        raise HTTPException(status_code=500, detail="Async query failed")


@app.post("/api/transform/verbatim", response_model=QueryResponse)
async def verbatim_transform_endpoint(request: VerbatimTransformRequest):
    """RAG-agnostic verbatim transform: question + context -> verbatim answer.

    The optional `answer` field is currently ignored.
    """
    from verbatim_rag.transform import VerbatimTransform

    try:
        vt = VerbatimTransform()
        # Convert Pydantic models to dicts expected by the transform
        context_dicts = [c.model_dump() for c in request.context]
        resp = await vt.transform_async(
            question=request.question, context=context_dicts, answer=request.answer
        )
        return resp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SpanExtractionUnavailable as e:
        raise _extraction_unavailable(e)
    except Exception as e:
        logger.error(f"Verbatim transform failed: {e}")
        raise HTTPException(status_code=500, detail="Verbatim transform failed")


@app.post("/api/query/async", response_model=QueryResponse)
async def query_async_slash_endpoint(
    request: QueryRequestModel,
    api_service: Annotated[APIService, Depends(get_api_service)],
    _: Annotated[bool, Depends(check_system_ready)],
):
    """
    Async query the RAG system

    Args:
        request: Query request with question and optional template ID

    Returns:
        Query response with answer and supporting documents
    """
    try:
        # Validate request
        api_service.validate_query_request(request.question)

        response = await api_service.query_async(
            request.question,
            k=request.k,
            hybrid_weights=request.hybrid_weights,
            rrf_k=request.rrf_k,
            filter=request.filter,
            search_params=request.search_params,
        )

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SpanExtractionUnavailable as e:
        raise _extraction_unavailable(e)
    except Exception as e:
        logger.error(f"Async query failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/templates", response_model=TemplateListResponse)
async def get_templates(
    template_manager: Annotated[TemplateManager, Depends(get_template_manager)],
):
    """Get available templates (return modes as simple records)."""
    try:
        modes = template_manager.get_available_modes()
        return TemplateListResponse(templates=[{"mode": m} for m in modes])
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve templates")


@app.post("/api/query/stream")
async def query_stream_endpoint(
    request: StreamQueryRequestModel,
    # No RAG dependency any more: the service builds the stream, and it already
    # depends on the same factory, so the singleton is still constructed here.
    api_service: Annotated[APIService, Depends(get_api_service)],
    _: Annotated[bool, Depends(check_system_ready)],
):
    """
    Stream a query response in stages using the package's streaming interface

    Args:
        request: Stream query request with question and optional num_docs

    Returns:
        Streaming response with documents, highlights, and final answer
    """
    try:
        # Validate request
        api_service.validate_query_request(request.question)

        # Same layer as the other two.

        async def generate_clean_response():
            """Clean response generator using the package's streaming interface"""
            import json

            logger.info(f"Starting streaming query for: {request.question}")

            try:
                stage_count = 0
                async for stage in api_service.stream_query(
                    request.question,
                    request.num_docs,
                    filter=request.filter,
                    hybrid_weights=request.hybrid_weights,
                    rrf_k=request.rrf_k,
                    search_params=request.search_params,
                ):
                    stage_count += 1
                    logger.info(f"Yielding stage {stage_count}: {stage.get('type', 'unknown')}")
                    yield json.dumps(stage) + "\n"

                if stage_count == 0:
                    logger.warning("No stages yielded from streaming query")
                    yield (
                        json.dumps(
                            {
                                "type": "error",
                                "error": "No data returned from RAG system",
                                "done": True,
                            }
                        )
                        + "\n"
                    )

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                import traceback

                traceback.print_exc()
                yield (json.dumps({"type": "error", "error": str(e), "done": True}) + "\n")

        # Return streaming response with proper headers
        return FastAPIStreamingResponse(
            generate_clean_response(),
            media_type="application/x-ndjson",
            headers={
                "Content-Type": "application/x-ndjson",
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "Transfer-Encoding": "chunked",
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stream query failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Serve static frontend files for production deployment (mounted last to not interfere with API routes)
if os.path.exists("./static"):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
