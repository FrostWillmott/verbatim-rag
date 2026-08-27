"""
Configuration management for the API
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class APIConfig(BaseSettings):
    """API configuration using Pydantic BaseSettings for environment variable handling.

    `validation_alias`, not `env`: the latter is a Pydantic v1 idiom that v2 keeps
    only as schema metadata, so every name below used to be inert. Without the
    aliases the fields bind to their own names instead, and the documented
    API_HOST / API_PORT / API_DEBUG do nothing at all.
    """

    # Server configuration
    host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    port: int = Field(default=8000, validation_alias="API_PORT")
    debug: bool = Field(default=False, validation_alias="API_DEBUG")

    # CORS configuration
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], validation_alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, validation_alias="CORS_ALLOW_CREDENTIALS")

    # RAG system paths
    # Two defaults on purpose, for two different ways of running this. Directly,
    # the database belongs next to the working directory; in the container it has
    # to be the mounted volume, and Compose supplies /data/index.db. Collapsing
    # them into one value would put the container's path on a direct run, or a
    # non-persistent relative path inside the image.
    index_path: Path = Field(default=Path("./index.db"), validation_alias="INDEX_PATH")
    templates_path: Path = Field(default=Path("templates"), validation_alias="TEMPLATES_PATH")

    # API limits
    max_question_length: int = Field(default=1000, validation_alias="MAX_QUESTION_LENGTH")

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # extra="ignore" because .env is shared with the rest of the stack: README tells
    # the user to put OPENAI_API_KEY there, and that key belongs to the LLM client,
    # not to this model. pydantic-settings forbids unknown keys by default, so
    # without this the documented setup made `import api.app` raise on the spot.
    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


def get_config() -> APIConfig:
    """Get API configuration instance"""
    return APIConfig()
