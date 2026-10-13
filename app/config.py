"""Application settings loaded from environment variables and the .env file."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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

    # Public deployment (all off by default for local use)
    # Shared password for every page (HTTP Basic); empty = no password.
    app_password: SecretStr = SecretStr("")
    # Max AI requests per client IP per minute; 0 = no limit.
    rate_limit_per_minute: int = Field(default=0, ge=0)
    # Shared demo: everyone uses one profile, so deleting data is disabled.
    public_demo: bool = False

    @model_validator(mode="after")
    def public_demo_needs_password(self) -> "Settings":
        """Refuse to start a public demo that anyone could open without a password."""
        if self.public_demo and not self.app_password.get_secret_value():
            raise ValueError("PUBLIC_DEMO=true requires APP_PASSWORD to be set.")
        return self

    @field_validator("database_url", "test_database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str | None) -> str | None:
        """Hosts such as Neon give "postgresql://"; SQLAlchemy needs the psycopg (v3) driver."""
        if url is None:
            return None
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so .env is read only once."""
    return Settings()
