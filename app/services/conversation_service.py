"""Conversation business logic: start conversations and run chat turns."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import conversation_not_found, request_id_conflict
from app.harness.chat_harness import ChatHarness, TurnResult
from app.harness.context import MAX_HISTORY_MESSAGES, ChatTurn, TurnContext
from app.harness.prompts import PROMPT_VERSION
from app.models import Conversation, Message
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import (
    CorrectionOut,
    CreateConversationRequest,
    MessageOut,
    SendMessageRequest,
    SendMessageResponse,
)
from app.schemas.error import ErrorBody

logger = logging.getLogger(__name__)

INVALID_AI_OUTPUT_ERROR = ErrorBody(
    code="invalid_ai_output",
    message_vi="AI trả về dữ liệu không hợp lệ. Câu của bạn vẫn được giữ, hãy thử lại.",
    retryable=True,
)
AI_UNAVAILABLE_ERROR = ErrorBody(
    code="ai_unavailable",
    message_vi="Không gọi được AI lúc này. Câu của bạn vẫn được giữ, hãy thử lại.",
    retryable=True,
)


class ConversationService:
    def __init__(self, session: Session, harness: ChatHarness) -> None:
        self._session = session
        self._repository = ConversationRepository(session)
        self._harness = harness

    def create_conversation(self, request: CreateConversationRequest) -> int:
        profile = self._repository.get_or_create_default_profile()
        # Settings chosen when starting a conversation become the profile settings.
        profile.level = request.level
        profile.correction_mode = request.correction_mode
        conversation = self._repository.create_conversation(profile.id, request.topic)
        self._session.commit()
        return conversation.id

    def send_message(
        self, conversation_id: int, request: SendMessageRequest
    ) -> SendMessageResponse:
        """Run one chat turn. Resending the same request_id never creates a second turn."""
        conversation = self._repository.get_conversation(conversation_id)
        if conversation is None:
            raise conversation_not_found()

        user_message, is_new = self._find_or_create_user_message(
            conversation_id, request
        )
        if not is_new:
            # Succeeded: return the stored result without calling the AI again.
            # Pending: another request with this id is still being processed.
            if user_message.status != "failed":
                return self._build_response(user_message)
            # Failed: retry the AI on the same message instead of creating a new one.
            user_message.status = "pending"
            self._session.commit()

        return self._run_turn(conversation, user_message)

    def _find_or_create_user_message(
        self, conversation_id: int, request: SendMessageRequest
    ) -> tuple[Message, bool]:
        existing = self._repository.find_message_by_request_id(request.request_id)
        if existing is not None:
            ensure_same_request(existing, conversation_id, request)
            return existing, False

        # Transaction 1: save the user's text before calling the AI, so it is never lost.
        try:
            message = self._repository.add_user_message(
                conversation_id, request.request_id, request.text, request.input_mode
            )
            self._session.commit()
        except IntegrityError:
            # A concurrent request inserted the same request_id first.
            self._session.rollback()
            existing = self._repository.find_message_by_request_id(request.request_id)
            if existing is None:
                raise
            ensure_same_request(existing, conversation_id, request)
            return existing, False
        return message, True

    def _run_turn(
        self, conversation: Conversation, user_message: Message
    ) -> SendMessageResponse:
        context = self._build_context(conversation, user_message)

        # No transaction is held open while waiting for the AI.
        try:
            result = self._harness.run_turn(context)
        except Exception:
            logger.exception("AI call failed: message_id=%d", user_message.id)
            result = None

        # Transaction 2: reply + corrections + status change are saved together.
        try:
            if result is not None and result.status == "succeeded":
                assert result.reply is not None
                self._repository.add_reply(user_message, result.reply, PROMPT_VERSION)
            else:
                user_message.status = "failed"
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        logger.info(
            "Chat turn saved: conversation_id=%d message_id=%d status=%s",
            conversation.id,
            user_message.id,
            user_message.status,
        )
        return self._build_response(user_message, error=failure_error(result))

    def _build_context(
        self, conversation: Conversation, user_message: Message
    ) -> TurnContext:
        history = self._repository.list_recent_turns(
            conversation.id, limit=MAX_HISTORY_MESSAGES
        )
        profile = conversation.profile
        return TurnContext(
            level=profile.level,
            correction_mode=profile.correction_mode,
            topic=conversation.topic,
            summary=conversation.summary,
            history=[ChatTurn(role=m.role, text=m.original_text) for m in history],
            user_text=user_message.original_text,
        )

    def _build_response(
        self, user_message: Message, error: ErrorBody | None = None
    ) -> SendMessageResponse:
        reply = self._repository.get_reply(user_message.id)
        return SendMessageResponse(
            status=user_message.status,
            message=to_message_out(user_message),
            reply=to_message_out(reply) if reply is not None else None,
            corrections=[
                CorrectionOut.model_validate(c) for c in user_message.corrections
            ],
            error=error,
        )


def ensure_same_request(
    message: Message, conversation_id: int, request: SendMessageRequest
) -> None:
    """A reused request_id must belong to the same conversation and text."""
    if (
        message.conversation_id != conversation_id
        or message.original_text != request.text
    ):
        raise request_id_conflict()


def failure_error(result: TurnResult | None) -> ErrorBody | None:
    if result is None:
        return AI_UNAVAILABLE_ERROR
    if result.status == "failed":
        return INVALID_AI_OUTPUT_ERROR
    return None


def to_message_out(message: Message) -> MessageOut:
    return MessageOut(
        id=message.id,
        role=message.role,
        text=message.original_text,
        status=message.status,
        created_at=message.created_at,
    )
