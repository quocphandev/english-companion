"""Application settings loaded from environment variables and the .env file."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration. Field names map to env vars case-insensitively."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str
    # Only needed by integration tests; must point to a separate database.
    test_database_url: str | None = None

    # AI
    ai_provider: Literal["fake", "gemini"] = "fake"
    gemini_api_key: SecretStr = SecretStr("")
    # Model name comes only from configuration, never hardcoded.
    gemini_model: str = ""
    # Empty means "use the model's default thinking level".
    gemini_thinking_level: Literal["", "minimal", "low", "medium", "high"] = ""
    ai_max_output_tokens: int = Field(default=800, gt=0)
    ai_timeout_seconds: int = Field(default=30, gt=0)
    daily_ai_limit: int = Field(default=100, ge=0)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so .env is read only once."""
    return Settings()
