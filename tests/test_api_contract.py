"""Contract tests for the FastAPI surface in api/app.py.

These run against doubles for the RAG and template seams, so they need neither
Milvus nor an LLM key. See the api_client fixture in conftest.py.
"""


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
    def test_num_docs_does_not_change_the_shared_retrieval_default(self, fake_rag):
        """The RAG object is a process-wide singleton.

        Before the fix a stream that raised left self.rag.k rewritten for every
        later request, so this asserts the value after an explicitly failing run.
        """
        import asyncio

        from verbatim_rag.streaming import StreamingRAG

        fake_rag.k = 5
        fake_rag.index.query.side_effect = RuntimeError("retrieval exploded")
        streamer = StreamingRAG(fake_rag)

        async def drain():
            return [stage async for stage in streamer.stream_query("q", num_docs=99)]

        stages = asyncio.run(drain())

        assert any(stage.get("type") == "error" for stage in stages)
        assert fake_rag.k == 5


class TestQueryEndpoint:
    """POST /api/query — synchronous route, bypasses APIService."""

    def test_returns_the_answer(self, api_client):
        response = api_client.post("/api/query", json={"question": "What is X?"})

        assert response.status_code == 200
        assert response.json()["answer"] == "X is Y."

    def test_rejects_an_empty_question(self, api_client):
        response = api_client.post("/api/query", json={"question": "   "})

        assert response.status_code == 400
