"""
Dependency injection setup for FastAPI
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException

from api.config import APIConfig, get_config
from api.services.rag_service import APIService
from verbatim_core.templates import TemplateManager
from verbatim_rag.core import LLMClient, VerbatimRAG

logger = logging.getLogger(__name__)


# Global instances (initialized once)
_rag_instance: VerbatimRAG = None
_template_manager: TemplateManager = None
_api_service: APIService = None


def apply_template_config(manager: TemplateManager, templates_path: Path) -> bool:
    """Load TEMPLATES_PATH into a template manager, if the file is there.

    Returns whether it was applied. Split out from the construction paths so the
    behaviour can be tested without standing up Milvus and an embedding model.
    """
    if not templates_path.exists():
        logger.info("Template config not found at %s; using built-in defaults", templates_path)
        return False

    manager.load(str(templates_path))
    logger.info("Template config loaded from %s", templates_path)
    return True


def get_rag_instance(config: Annotated[APIConfig, Depends(get_config)]) -> VerbatimRAG:
    """Get or create RAG instance (singleton)"""
    global _rag_instance

    if _rag_instance is None:
        try:
            from verbatim_rag.embedding_providers import SentenceTransformersProvider
            from verbatim_rag.index import VerbatimIndex
            from verbatim_rag.vector_stores import LocalMilvusStore

            llm_client = LLMClient(
                model=config.llm_model,
                api_base=config.llm_api_base,
            )

            dense_provider = SentenceTransformersProvider(
                model_name="ibm-granite/granite-embedding-small-english-r2",
                device="cpu",
            )

            # Create vector store
            vector_store = LocalMilvusStore(
                db_path=str(config.index_path),
                collection_name="acl",
                enable_dense=True,
                enable_sparse=False,
                dense_dim=dense_provider.get_dimension(),
            )

            # Create index
            index = VerbatimIndex(vector_store=vector_store, dense_provider=dense_provider)

            # Create RAG instance with the index
            _rag_instance = VerbatimRAG(
                index=index,
                k=5,
                template_mode="contextual",
                llm_client=llm_client,
            )
            # The manager VerbatimRAG builds for itself is the one that renders
            # answers. Loading the config into the separate manager behind
            # /api/templates left TEMPLATES_PATH with no effect on any query.
            # Passing that manager in instead would be wrong: it is built without
            # an llm_client and defaults to "static", so contextual mode would
            # break and every answer's framing would change silently.
            apply_template_config(_rag_instance.template_manager, config.templates_path)

            logger.info(f"RAG instance created with index path: {config.index_path}")
        except Exception as e:
            logger.error(f"Failed to create RAG instance: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to initialize RAG system: {str(e)}"
            )

    return _rag_instance


def get_template_manager(
    config: Annotated[APIConfig, Depends(get_config)],
) -> TemplateManager:
    """Get or create template manager (singleton)"""
    global _template_manager

    if _template_manager is None:
        try:
            _template_manager = TemplateManager()
            apply_template_config(_template_manager, config.templates_path)
        except Exception as e:
            logger.error(f"Failed to create template manager: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize template manager: {str(e)}",
            )

    return _template_manager


def get_api_service(
    rag: Annotated[VerbatimRAG, Depends(get_rag_instance)],
    template_manager: Annotated[TemplateManager, Depends(get_template_manager)],
    config: Annotated[APIConfig, Depends(get_config)],
) -> APIService:
    """Get API service instance"""
    global _api_service

    if _api_service is None:
        _api_service = APIService(
            rag, template_manager, max_question_length=config.max_question_length
        )
        logger.info("API service created")

    return _api_service


def check_system_ready(rag: Annotated[VerbatimRAG, Depends(get_rag_instance)]) -> bool:
    """Check if the RAG system is ready to handle requests"""
    try:
        # Check if index is loaded
        if not hasattr(rag, "index") or rag.index is None:
            raise HTTPException(
                status_code=503, detail="RAG system is not ready. Index not loaded."
            )
        return True
    except Exception as e:
        logger.error(f"System readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="RAG system is not ready")
