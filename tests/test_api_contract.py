"""Contract tests for the FastAPI surface in api/app.py.

These run against doubles for the RAG and template seams, so they need neither
Milvus nor an LLM key. See the api_client fixture in conftest.py.
"""

import pytest

# Needs the root package installed, not just verbatim-core: this exercises the
# RAG and API surfaces. CI runs these in a separate job — see requires_full_stack
# in pyproject.toml.
pytestmark = pytest.mark.requires_full_stack


class TestQueryAsyncEndpoint:
    """POST /api/query_async — the one route that goes through APIService."""

    def test_returns_the_answer(self, api_client):
        response = api_client.post("/api/query_async", json={"question": "What is X?"})

        assert response.status_code == 200
        assert response.json()["answer"] == "X is Y."

    def test_forwards_search_arguments_to_the_rag_layer(self, api_client, fake_rag):
        api_client.post(
            "/api/query_async",
            json={
                "question": "What is X?",
                "k": 3,
                "filter": "user_id == 'alice'",
                "search_params": {"nprobe": 8},
            },
        )

        assert fake_rag.query_async.await_count == 1
        kwargs = fake_rag.query_async.await_args.kwargs
        assert kwargs["k"] == 3
        assert kwargs["filter"] == "user_id == 'alice'"
        assert kwargs["search_params"] == {"nprobe": 8}


class TestQuerySlashAsyncEndpoint:
    """POST /api/query/async — near-duplicate of the above that bypasses APIService.

    Pinned before the two routes are reconciled, so the reconciliation cannot
    silently change what a client already gets from the working one.
    """

    def test_returns_the_answer(self, api_client):
        response = api_client.post("/api/query/async", json={"question": "What is X?"})

        assert response.status_code == 200
        assert response.json()["answer"] == "X is Y."

    def test_forwards_search_arguments_to_the_rag_layer(self, api_client, fake_rag):
        api_client.post(
            "/api/query/async",
            json={"question": "What is X?", "filter": "user_id == 'alice'"},
        )

        assert fake_rag.query_async.await_args.kwargs["filter"] == "user_id == 'alice'"


class TestDeclaredSettingsTakeEffect:
    """Settings the API advertises have to change what the API does."""

    def test_max_question_length_is_enforced(self, api_client):
        from api.app import app
        from api.config import APIConfig, get_config

        app.dependency_overrides[get_config] = lambda: APIConfig(
            _env_file=None, max_question_length=10
        )

        response = api_client.post("/api/query", json={"question": "x" * 50})

        assert response.status_code == 400
        assert "10" in response.json()["detail"]

    def test_a_question_within_the_configured_limit_is_accepted(self, api_client):
        from api.app import app
        from api.config import APIConfig, get_config

        app.dependency_overrides[get_config] = lambda: APIConfig(
            _env_file=None, max_question_length=10
        )

        response = api_client.post("/api/query", json={"question": "x" * 5})

        assert response.status_code == 200


class TestTemplateIdIsGone:
    """template_id reached no consumer, so the schema no longer offers it."""

    def test_not_advertised_in_the_openapi_schema(self, api_client):
        schema = api_client.get("/openapi.json").json()

        properties = schema["components"]["schemas"]["QueryRequestModel"]["properties"]
        assert "template_id" not in properties

    def test_sending_it_is_rejected_rather_than_silently_ignored(self, api_client):
        response = api_client.post(
            "/api/query", json={"question": "What is X?", "template_id": "anything"}
        )

        assert response.status_code == 422

    def test_the_streaming_route_refuses_unknown_fields_too(self, api_client):
        # The route the live UI uses. Forbidding extras on /api/query alone would
        # have left the honest-contract property off the one that matters most.
        response = api_client.post(
            "/api/query/stream", json={"question": "What is X?", "template_id": "anything"}
        )

        assert response.status_code == 422

    def test_the_payload_the_live_ui_sends_is_still_accepted(self, api_client):
        # frontend/src/contexts/ApiContext.js posts exactly these two fields.
        response = api_client.post(
            "/api/query/stream", json={"question": "What is X?", "num_docs": 5}
        )

        assert response.status_code == 200


class TestLlmKeyIsReportedNotGuessed:
    """An empty key is as missing as an absent one, and both are visible early.

    The stack deliberately starts without a key — .env.example says so — so the
    fix is an honest signal, not a hard failure.
    """

    def test_absent_key_counts_as_unconfigured(self, monkeypatch):
        from api.app import llm_key_is_configured

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        assert llm_key_is_configured() is False

    def test_empty_key_counts_as_unconfigured(self, monkeypatch):
        from api.app import llm_key_is_configured

        # .env.example ships OPENAI_API_KEY= — the likeliest way to end up broken.
        monkeypatch.setenv("OPENAI_API_KEY", "")

        assert llm_key_is_configured() is False

    def test_whitespace_key_counts_as_unconfigured(self, monkeypatch):
        from api.app import llm_key_is_configured

        monkeypatch.setenv("OPENAI_API_KEY", "   ")

        assert llm_key_is_configured() is False

    def test_a_real_key_counts_as_configured(self, monkeypatch):
        from api.app import llm_key_is_configured

        monkeypatch.setenv("OPENAI_API_KEY", "sk-something")

        assert llm_key_is_configured() is True

    def test_status_reports_the_key_state(self, api_client, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")

        body = api_client.get("/api/status").json()

        assert body["llm_configured"] is False


class TestStatusDistinguishesAnEmptyIndex:
    """A green "Ready" over an empty index is the one lie the badge must not tell.

    Found by a manual pass over the running stack, not by any of the reports: the
    UI showed "✓ Ready" while every question answered "No relevant information
    found in the provided documents."
    """

    def test_a_populated_index_reports_its_document_count(self, api_client):
        body = api_client.get("/api/status").json()

        assert body["document_count"] == 2

    def test_a_populated_index_is_reported_ready(self, api_client):
        body = api_client.get("/api/status").json()

        assert body["message"] == "RAG system ready"

    def test_an_empty_index_reports_zero_documents(self, api_client, fake_rag):
        fake_rag.index.vector_store.get_all_documents.return_value = []

        body = api_client.get("/api/status").json()

        assert body["document_count"] == 0

    def test_an_empty_index_says_so_in_the_message(self, api_client, fake_rag):
        fake_rag.index.vector_store.get_all_documents.return_value = []

        body = api_client.get("/api/status").json()

        assert body["message"] == "RAG system ready, but no documents are indexed"

    def test_a_store_that_cannot_count_reports_none_not_zero(self, api_client, fake_rag):
        # "Unknown" and "empty" are different answers, and only one of them means
        # the operator forgot to ingest anything.
        del fake_rag.index.vector_store.get_all_documents

        body = api_client.get("/api/status").json()

        assert body["document_count"] is None


class TestExpensiveRequestsAreBounded:
    """A single caller should not be able to ask for unbounded retrieval."""

    def test_num_docs_above_the_cap_is_rejected(self, api_client):
        response = api_client.post(
            "/api/query/stream", json={"question": "What is X?", "num_docs": 10**6}
        )

        assert response.status_code == 422

    def test_num_docs_below_one_is_rejected(self, api_client):
        response = api_client.post(
            "/api/query/stream", json={"question": "What is X?", "num_docs": 0}
        )

        assert response.status_code == 422

    def test_k_above_the_cap_is_rejected(self, api_client):
        response = api_client.post("/api/query", json={"question": "What is X?", "k": 10**6})

        assert response.status_code == 422

    def test_context_item_count_is_capped(self, api_client):
        response = api_client.post(
            "/api/transform/verbatim",
            json={
                "question": "What is X?",
                "context": [{"content": "x"} for _ in range(10_000)],
            },
        )

        assert response.status_code == 422


class TestStreamingLeavesSharedStateAlone:
    """The RAG object is a process-wide singleton.

    Before the fix, a stream that raised left self.rag.k rewritten for every later
    request in the process, and two concurrent streams overwrote each other even
    when both succeeded.
    """

    @staticmethod
    def _drain(streamer, **kwargs):
        import asyncio

        async def run():
            return [stage async for stage in streamer.stream_query("q", **kwargs)]

        return asyncio.run(run())

    @staticmethod
    def _streamer(fake_rag):
        from unittest.mock import AsyncMock

        from verbatim_rag.streaming import StreamingRAG

        # Awaitable, and returning None so the intent check does not short-circuit.
        # Without this the generator dies on `await MagicMock()` before retrieval,
        # and the test would pass for a reason that has nothing to do with k.
        fake_rag._detect_intent_async = AsyncMock(return_value=None)
        fake_rag.k = 5
        return StreamingRAG(fake_rag)

    def test_num_docs_is_used_for_retrieval_without_being_stored(self, fake_rag):
        streamer = self._streamer(fake_rag)
        fake_rag.index.query.side_effect = RuntimeError("retrieval exploded")

        stages = self._drain(streamer, num_docs=99)

        assert [stage["type"] for stage in stages] == ["error"]
        assert fake_rag.index.query.call_args.kwargs["k"] == 99
        assert fake_rag.k == 5

    def test_the_shared_default_is_used_when_num_docs_is_omitted(self, fake_rag):
        streamer = self._streamer(fake_rag)
        fake_rag.index.query.side_effect = RuntimeError("retrieval exploded")

        self._drain(streamer)

        assert fake_rag.index.query.call_args.kwargs["k"] == 5


class TestFilterIsBounded:
    """`filter` reaches a Milvus expression parser, so the API narrows it.

    Not a redesign of the library's query API, which stays as it is — this is a
    guard at the HTTP boundary, which the README calls a prototype surface.
    """

    def test_a_simple_equality_is_accepted(self, api_client, fake_rag):
        response = api_client.post(
            "/api/query", json={"question": "What is X?", "filter": "user_id == 'alice'"}
        )

        assert response.status_code == 200
        assert fake_rag.query.call_args.kwargs["filter"] == "user_id == 'alice'"

    def test_two_terms_joined_by_and_are_accepted(self, api_client):
        response = api_client.post(
            "/api/query",
            json={
                "question": "What is X?",
                "filter": "user_id == 'alice' and dataset_id == 'papers'",
            },
        )

        assert response.status_code == 200

    def test_a_disjunction_that_widens_the_scope_is_refused(self, api_client):
        response = api_client.post(
            "/api/query",
            json={"question": "What is X?", "filter": "user_id == 'alice' or 1 == 1"},
        )

        assert response.status_code == 422

    def test_a_field_outside_the_allowlist_is_refused(self, api_client):
        response = api_client.post(
            "/api/query", json={"question": "What is X?", "filter": "secret == 'x'"}
        )

        assert response.status_code == 422

    def test_a_quote_inside_the_value_is_refused(self, api_client):
        response = api_client.post(
            "/api/query", json={"question": "What is X?", "filter": "user_id == 'a' == 'b'"}
        )

        assert response.status_code == 422

    def test_the_streaming_route_is_guarded_too(self, api_client):
        response = api_client.post(
            "/api/query/stream",
            json={"question": "What is X?", "filter": "user_id == 'a' or 1 == 1"},
        )

        assert response.status_code == 422


class TestQueryEndpoint:
    """POST /api/query — synchronous route, bypasses APIService."""

    def test_returns_the_answer(self, api_client):
        response = api_client.post("/api/query", json={"question": "What is X?"})

        assert response.status_code == 200
        assert response.json()["answer"] == "X is Y."

    def test_rejects_an_empty_question(self, api_client):
        response = api_client.post("/api/query", json={"question": "   "})

        assert response.status_code == 400


class TestLlmProviderComesFromSettings:
    """The model and endpoint were constants in api/dependencies.py, so pointing
    the demo at another provider — or at a model a given key can actually reach —
    meant editing source. They are settings now, and the two things worth pinning
    are that the defaults did not move and that the values are not inert: BEY-6
    was a whole set of documented variables that reached nothing.
    """

    def test_defaults_are_the_constants_they_replaced(self):
        from api.config import APIConfig

        config = APIConfig(_env_file=None)

        assert config.llm_model == "moonshotai/kimi-k2-instruct-0905"
        assert config.llm_api_base == "https://api.groq.com/openai/v1/"

    def test_the_environment_selects_the_model_and_the_endpoint(self, monkeypatch):
        from api.config import APIConfig

        monkeypatch.setenv("LLM_MODEL", "qwen/qwen3.8-27b")
        monkeypatch.setenv("LLM_API_BASE", "https://api.openai.com/v1")

        config = APIConfig(_env_file=None)

        assert config.llm_model == "qwen/qwen3.8-27b"
        assert config.llm_api_base == "https://api.openai.com/v1"

    def test_the_factory_builds_the_client_from_them(self, monkeypatch, tmp_path):
        """The assertion that stops a repeat of BEY-6: the settings reach the client."""
        from api import dependencies
        from api.config import APIConfig
        from verbatim_rag import embedding_providers, vector_stores
        from verbatim_rag import index as index_module

        recorded: dict[str, str] = {}

        class RecordingLLMClient:
            def __init__(self, model: str, api_base: str):
                recorded["model"] = model
                recorded["api_base"] = api_base

        class FakeProvider:
            def __init__(self, **kwargs):
                pass

            def get_dimension(self) -> int:
                return 384

        class FakeRag:
            def __init__(self, **kwargs):
                self.template_manager = object()

        monkeypatch.setattr(dependencies, "_rag_instance", None)
        monkeypatch.setattr(dependencies, "LLMClient", RecordingLLMClient)
        monkeypatch.setattr(dependencies, "VerbatimRAG", FakeRag)
        monkeypatch.setattr(embedding_providers, "SentenceTransformersProvider", FakeProvider)
        monkeypatch.setattr(vector_stores, "LocalMilvusStore", lambda **kwargs: object())
        monkeypatch.setattr(index_module, "VerbatimIndex", lambda **kwargs: object())

        dependencies.get_rag_instance(
            APIConfig(
                _env_file=None,
                llm_model="qwen/qwen3.8-27b",
                llm_api_base="https://api.openai.com/v1",
                templates_path=tmp_path / "absent.json",
            )
        )

        assert recorded == {
            "model": "qwen/qwen3.8-27b",
            "api_base": "https://api.openai.com/v1",
        }
