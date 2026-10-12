"""Conversation business logic: start conversations and run chat turns."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import conversation_not_found, request_id_conflict
from app.harness.chat_harness import ChatHarness, TurnResult
from app.harness.context import MAX_HISTORY_MESSAGES, ChatTurn, TurnContext
from app.harness.prompts import PROMPT_VERSION
from app.models import Conversation, Message
from app.providers.errors import ProviderError
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import (
    ConversationHistory,
    ConversationSummary,
    CorrectionOut,
    CreateConversationRequest,
    MessageOut,
    SendMessageRequest,
    SendMessageResponse,
    TurnView,
)
from app.schemas.error import ErrorBody
from app.services.ai_usage import AiUsage
from app.services.correction_view import build_correction_view

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(
        self, session: Session, harness: ChatHarness, daily_ai_limit: int
    ) -> None:
        self._session = session
        self._repository = ConversationRepository(session)
        self._ai_usage = AiUsage(session, harness, daily_ai_limit)
        self._harness = harness

    def create_conversation(self, request: CreateConversationRequest) -> int:
        profile = self._repository.get_or_create_default_profile()
        # The conversation keeps its own settings; the profile remembers the
        # latest choice as the default for the next conversation.
        profile.level = request.level
        profile.correction_mode = request.correction_mode
        conversation = self._repository.create_conversation(
            profile.id, request.topic, request.level, request.correction_mode
        )
        self._session.commit()
        return conversation.id

    def list_conversations(self) -> list[ConversationSummary]:
        return [
            ConversationSummary(id=c.id, topic=c.topic, created_at=c.created_at)
            for c in self._repository.list_conversations()
        ]

    def get_history(self, conversation_id: int) -> ConversationHistory | None:
        """Conversation with its turns in order, or None if it does not exist."""
        conversation = self._repository.get_conversation(conversation_id)
        if conversation is None:
            return None
        messages = self._repository.list_messages(conversation_id)
        return ConversationHistory(
            id=conversation.id,
            topic=conversation.topic,
            level=conversation.level,
            correction_mode=conversation.correction_mode,
            turns=group_turns(messages),
        )

    def send_message(
        self, conversation_id: int, request: SendMessageRequest
    ) -> SendMessageResponse:
        """Run one chat turn. Resending the same request_id never creates a second turn."""
        conversation = self._repository.get_conversation(conversation_id)
        if conversation is None:
            raise conversation_not_found()

        existing = self._repository.find_message_by_request_id(request.request_id)
        if existing is not None:
            return self._handle_existing(conversation, existing, request)

        self._ai_usage.ensure_within_daily_limit(conversation.profile.timezone)
        # Transaction 1: save the user's text before calling the AI, so it is never lost.
        try:
            user_message = self._repository.add_user_message(
                conversation_id, request.request_id, request.text, request.input_mode
            )
            self._session.commit()
        except IntegrityError:
            # A concurrent request inserted the same request_id first.
            self._session.rollback()
            existing = self._repository.find_message_by_request_id(request.request_id)
            if existing is None:
                raise
            return self._handle_existing(conversation, existing, request)
        return self._run_turn(conversation, user_message)

    def _handle_existing(
        self, conversation: Conversation, message: Message, request: SendMessageRequest
    ) -> SendMessageResponse:
        """A resend of a known request_id: never creates a second turn."""
        ensure_same_request(message, conversation.id, request)
        # Succeeded: return the stored result without calling the AI again.
        # Pending: another request with this id is still being processed.
        if message.status != "failed":
            return self._build_response(message)
        # Failed: retry the AI on the same message instead of creating a new one.
        self._ai_usage.ensure_within_daily_limit(conversation.profile.timezone)
        message.status = "pending"
        self._session.commit()
        return self._run_turn(conversation, message)

    def _run_turn(
        self, conversation: Conversation, user_message: Message
    ) -> SendMessageResponse:
        context = self._build_context(conversation, user_message)

        # No transaction is held open while waiting for the AI.
        try:
            result = self._harness.run_turn(context)
        except Exception:
            # Expected provider failures come back as a failed TurnResult;
            # this only catches unexpected bugs so the turn never stays pending.
            logger.exception(
                "Unexpected error in chat turn: message_id=%d", user_message.id
            )
            result = None

        # Transaction 2: reply + corrections + status change are saved together.
        try:
            if result is not None and result.status == "succeeded":
                assert result.reply is not None
                self._repository.add_reply(user_message, result.reply, PROMPT_VERSION)
            else:
                user_message.status = "failed"
            self._record_run(user_message, result)
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

    def _record_run(self, user_message: Message, result: TurnResult | None) -> None:
        self._ai_usage.record(
            operation="chat_turn",
            request_id=user_message.request_id,
            prompt_version=PROMPT_VERSION,
            error=failure_error(result),
            # Unknown after an unexpected crash: count one call to stay on the safe side.
            call_count=result.attempts if result is not None else 1,
            duration_ms=result.duration_ms if result is not None else 0,
        )

    def _build_context(
        self, conversation: Conversation, user_message: Message
    ) -> TurnContext:
        history = self._repository.list_recent_turns(
            conversation.id, limit=MAX_HISTORY_MESSAGES
        )
        return TurnContext(
            level=conversation.level,
            correction_mode=conversation.correction_mode,
            topic=conversation.topic,
            summary=conversation.summary,
            history=[ChatTurn(role=m.role, text=m.original_text) for m in history],
            user_text=user_message.original_text,
        )

    def _build_response(
        self, user_message: Message, error: ErrorBody | None = None
    ) -> SendMessageResponse:
        reply = self._repository.get_reply(user_message.id)
        corrections = to_corrections_out(user_message)
        return SendMessageResponse(
            status=user_message.status,
            message=to_message_out(user_message),
            reply=to_message_out(reply) if reply is not None else None,
            corrections=corrections,
            correction_view=build_correction_view(
                user_message.original_text, corrections
            ),
            error=error,
        )


def group_turns(messages: list[Message]) -> list[TurnView]:
    """Pair each user message with the assistant reply that answers it."""
    replies = {
        m.reply_to_message_id: m for m in messages if m.reply_to_message_id is not None
    }
    turns = []
    for message in messages:
        if message.role != "user":
            continue
        corrections = to_corrections_out(message)
        reply = replies.get(message.id)
        turns.append(
            TurnView(
                message=to_message_out(message),
                reply=to_message_out(reply) if reply is not None else None,
                corrections=corrections,
                correction_view=build_correction_view(
                    message.original_text, corrections
                ),
            )
        )
    return turns


def to_corrections_out(message: Message) -> list[CorrectionOut]:
    return [CorrectionOut.model_validate(c) for c in message.corrections]


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
        return ProviderError("ai_unavailable").to_error_body()
    return result.error


def to_message_out(message: Message) -> MessageOut:
    return MessageOut(
        id=message.id,
        role=message.role,
        text=message.original_text,
        status=message.status,
        created_at=message.created_at,
    )
