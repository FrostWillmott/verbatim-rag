"""Tests for api.config.APIConfig.

These need no FastAPI app and no RAG stack: APIConfig is constructed directly,
with the env file pointed at a temporary path so the developer's own .env cannot
change the result.
"""

from api.config import APIConfig


class TestEnvFile:
    def test_ignores_keys_that_belong_to_the_rest_of_the_stack(self, tmp_path):
        # The README tells the user to put OPENAI_API_KEY in .env, and that key is
        # read by the LLM client, not by this model. Rejecting it made importing
        # api.app raise, because create_app() builds the config at import time.
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-not-a-real-key\nINDEX_PATH=/data/index.db\n")

        config = APIConfig(_env_file=env_file)

        assert str(config.index_path) == "/data/index.db"


class TestDocumentedEnvironmentNames:
    def test_api_host_is_honoured(self, monkeypatch):
        monkeypatch.setenv("API_HOST", "127.0.0.1")

        assert APIConfig(_env_file=None).host == "127.0.0.1"

    def test_api_port_is_honoured(self, monkeypatch):
        monkeypatch.setenv("API_PORT", "9999")

        assert APIConfig(_env_file=None).port == 9999

    def test_max_question_length_is_honoured(self, monkeypatch):
        monkeypatch.setenv("MAX_QUESTION_LENGTH", "42")

        assert APIConfig(_env_file=None).max_question_length == 42

    def test_log_level_reaches_the_logging_configuration(self, monkeypatch):
        import logging

        from api.app import create_app

        previous = logging.getLogger().level
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        try:
            create_app()
            assert logging.getLogger().level == logging.DEBUG
        finally:
            logging.getLogger().setLevel(previous)

    def test_defaults_apply_when_nothing_is_set(self):
        config = APIConfig(_env_file=None)

        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.max_question_length == 1000
        # Deliberately relative: the container gets /data/index.db from Compose.
        assert str(config.index_path) == "index.db"
