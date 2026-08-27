from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_openai_response():
    """Factory for creating mock OpenAI completion responses."""

    def _make(content: str):
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = content
        return response

    return _make


@pytest.fixture
def mock_llm_client(mock_openai_response):
    """LLMClient with mocked OpenAI sync and async clients."""
    with patch("verbatim_core.llm_client.openai") as mock_openai:
        mock_sync = MagicMock()
        mock_async = AsyncMock()
        mock_openai.OpenAI.return_value = mock_sync
        mock_openai.AsyncOpenAI.return_value = mock_async

        from verbatim_core.llm_client import LLMClient

        client = LLMClient(model="test-model")

        yield client, mock_sync, mock_async, mock_openai_response


@pytest.fixture
def sample_spans():
    """Sample display and citation spans for template tests."""
    display = [
        {"text": "The study found that X leads to Y.", "doc_text": "doc1"},
        {"text": "Results show Z is significant.", "doc_text": "doc2"},
    ]
    citation = [
        {"text": "Additional context about the methodology.", "doc_text": "doc3"},
    ]
    return display, citation


@pytest.fixture
def make_query_response():
    """Factory for a minimal valid QueryResponse."""

    def _make(question: str = "What is X?", answer: str = "X is Y."):
        from verbatim_core.models import QueryResponse, StructuredAnswer

        return QueryResponse(
            question=question,
            answer=answer,
            structured_answer=StructuredAnswer(text=answer, citations=[]),
            documents=[],
        )

    return _make


@pytest.fixture
def fake_rag(make_query_response):
    """VerbatimRAG double that needs neither Milvus nor an LLM.

    `index` is set because check_system_ready refuses the request without it.
    """
    rag = MagicMock()
    rag.index = MagicMock()
    rag.k = 5
    rag.query.return_value = make_query_response()
    rag.query_async = AsyncMock(return_value=make_query_response())
    return rag


@pytest.fixture
def api_client(fake_rag):
    """TestClient with the two constructor seams replaced by doubles.

    Only get_rag_instance and get_template_manager are overridden: get_api_service
    is left alone so the real APIService sits in the request path, which is where
    the service layer's own defects live. The module-level singletons are reset
    around each test because get_api_service caches its instance in a global.
    """
    from fastapi.testclient import TestClient

    import api.dependencies as deps
    from api.app import app
    from api.config import APIConfig, get_config

    def _reset_singletons():
        deps._rag_instance = None
        deps._template_manager = None
        deps._api_service = None

    _reset_singletons()
    # Built with _env_file=None so the suite is hermetic: APIConfig otherwise reads
    # whatever .env the developer happens to have, and the result differs between
    # a clean checkout and a configured one.
    app.dependency_overrides[get_config] = lambda: APIConfig(_env_file=None)
    app.dependency_overrides[deps.get_rag_instance] = lambda: fake_rag
    # A lambda, not MagicMock itself: FastAPI introspects the override's signature,
    # and MagicMock's turns `args`/`kw` into required query parameters.
    app.dependency_overrides[deps.get_template_manager] = lambda: MagicMock()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    _reset_singletons()


@pytest.fixture
def make_search_result():
    """Factory for creating mock search result objects."""

    def _make(text, title="", source="", score=1.0):
        result = MagicMock()
        result.text = text
        result.metadata = {"title": title, "source": source}
        result.id = "test_id"
        result.score = score
        return result

    return _make
