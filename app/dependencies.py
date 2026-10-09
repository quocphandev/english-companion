"""FastAPI dependencies: build the objects each request needs.

Tests replace these with app.dependency_overrides (test DB session, scripted AI).
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.harness.chat_harness import ChatHarness
from app.providers.ai_provider import AIProvider
from app.providers.fake_provider import FakeProvider
from app.providers.gemini_provider import GeminiProvider
from app.services.conversation_service import ConversationService


def create_provider(settings: Settings) -> AIProvider:
    """Pick the AI provider from AI_PROVIDER ("fake" by default, or "gemini")."""
    if settings.ai_provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key.get_secret_value(),
            model=settings.gemini_model,
            timeout_seconds=settings.ai_timeout_seconds,
            thinking_level=settings.gemini_thinking_level,
        )
    return FakeProvider()


@lru_cache
def get_provider() -> AIProvider:
    """One provider (and so one HTTP client) for the whole app."""
    return create_provider(get_settings())


def get_harness() -> ChatHarness:
    return ChatHarness(get_provider(), get_settings().ai_max_output_tokens)


def get_conversation_service(
    session: Annotated[Session, Depends(get_session)],
    harness: Annotated[ChatHarness, Depends(get_harness)],
) -> ConversationService:
    return ConversationService(session, harness)


ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]
