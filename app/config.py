"""Application settings loaded from environment variables and the .env file."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration. Field names map to env vars case-insensitively."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str
    # Only needed by integration tests; must point to a separate database.
    test_database_url: str | None = None

    # AI
    ai_provider: Literal["fake", "claude"] = "fake"
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_model: str = ""
    ai_max_output_tokens: int = 800
    daily_ai_limit: int = 100


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so .env is read only once."""
    return Settings()
