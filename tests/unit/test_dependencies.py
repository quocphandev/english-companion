from typing import Any

from app.config import Settings
from app.dependencies import create_provider
from app.providers.fake_provider import FakeProvider
from app.providers.gemini_provider import GeminiProvider


def make_settings(**overrides: Any) -> Settings:
    # _env_file=None: ignore the real .env so the test is the same on every machine.
    return Settings(
        _env_file=None, database_url="postgresql+psycopg://unused", **overrides
    )


def test_fake_is_the_default_provider() -> None:
    assert isinstance(create_provider(make_settings()), FakeProvider)


def test_gemini_provider_is_built_from_settings() -> None:
    settings = make_settings(
        ai_provider="gemini",
        gemini_api_key="key-from-settings",
        gemini_model="model-from-settings",
        ai_timeout_seconds=12,
    )

    provider = create_provider(settings)

    assert isinstance(provider, GeminiProvider)
