"""FastAPI dependencies: build the objects each request needs.

Tests replace these with app.dependency_overrides (test DB session, scripted AI).
"""

from typing import Annotated

from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.harness.chat_harness import ChatHarness
from app.providers.fake_provider import FakeProvider
from app.services.conversation_service import ConversationService


def get_harness() -> ChatHarness:
    settings = get_settings()
    if settings.ai_provider != "fake":
        # The Claude provider arrives in milestone 2.
        raise AppError(
            "provider_not_supported",
            "Nhà cung cấp AI này chưa được hỗ trợ.",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return ChatHarness(FakeProvider(), settings.ai_max_output_tokens)


def get_conversation_service(
    session: Annotated[Session, Depends(get_session)],
    harness: Annotated[ChatHarness, Depends(get_harness)],
) -> ConversationService:
    return ConversationService(session, harness)


ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]
