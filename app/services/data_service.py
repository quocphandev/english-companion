"""Deleting learning data (SPEC section 9) and flagging replies for review.

- Deleting a conversation removes its messages, corrections, help requests and
  source links (database cascades); saved words are kept, without the link.
- "Delete all learning data" removes conversations, saved words (with their
  reviews) and cached lookups. ai_runs is usage metadata for the daily limit and
  is kept, so the limit cannot be reset by deleting data.
"""

from fastapi import status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.errors import AppError, conversation_not_found
from app.models import Conversation, LookupCache, Message, Vocabulary
from app.repositories.ai_run_repository import AiRunRepository
from app.repositories.conversation_repository import ConversationRepository

DELETE_ALL_CONFIRMATION = "XÓA TẤT CẢ"


def confirmation_mismatch() -> AppError:
    return AppError(
        "confirmation_mismatch",
        f"Hãy gõ đúng “{DELETE_ALL_CONFIRMATION}” để xác nhận.",
        http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


def reply_not_found() -> AppError:
    return AppError(
        "reply_not_found",
        "Không tìm thấy phản hồi của chatbot.",
        http_status=status.HTTP_404_NOT_FOUND,
    )


class DataService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._conversations = ConversationRepository(session)

    def delete_conversation(self, conversation_id: int) -> None:
        conversation = self._conversations.get_conversation(conversation_id)
        if conversation is None:
            raise conversation_not_found()
        self._session.delete(conversation)
        self._session.commit()

    def delete_all(self, confirmation: str) -> None:
        if confirmation.strip().upper() != DELETE_ALL_CONFIRMATION:
            raise confirmation_mismatch()
        profile = self._conversations.get_or_create_default_profile()
        self._session.execute(
            delete(Conversation).where(Conversation.profile_id == profile.id)
        )
        self._session.execute(
            delete(Vocabulary).where(Vocabulary.profile_id == profile.id)
        )
        # Cached lookups contain sentences from the deleted conversations.
        self._session.execute(delete(LookupCache))
        self._session.commit()

    def set_needs_review(self, message_id: int, needs_review: bool) -> bool:
        message = self._session.get(Message, message_id)
        if message is None or message.role != "assistant":
            raise reply_not_found()
        message.needs_review = needs_review
        self._session.commit()
        return message.needs_review

    def calls_today(self) -> int:
        """Real AI calls made today (profile time zone); the fake provider is not counted."""
        profile = self._conversations.get_or_create_default_profile()
        return AiRunRepository(self._session).count_calls_today(profile.timezone)
