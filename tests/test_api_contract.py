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


class TestQueryEndpoint:
    """POST /api/query — synchronous route, bypasses APIService."""

    def test_returns_the_answer(self, api_client):
        response = api_client.post("/api/query", json={"question": "What is X?"})

        assert response.status_code == 200
        assert response.json()["answer"] == "X is Y."

    def test_rejects_an_empty_question(self, api_client):
        response = api_client.post("/api/query", json={"question": "   "})

        assert response.status_code == 400
