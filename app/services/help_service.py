"""FR03: help the learner continue when stuck. Suggestions are never sent as messages."""

import logging

from sqlalchemy.orm import Session

from app.errors import conversation_finished, conversation_not_found
from app.harness.chat_harness import ChatHarness, TaskResult
from app.harness.context import MAX_HISTORY_MESSAGES, ChatTurn
from app.harness.help_context import HelpContext, help_mode_for
from app.harness.prompts import HELP_PROMPT_VERSION
from app.providers.errors import ProviderError
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.ai import HelpReply
from app.schemas.error import ErrorBody
from app.schemas.help import HelpRequestIn, HelpResponse
from app.services.ai_usage import AiUsage

logger = logging.getLogger(__name__)


class HelpService:
    def __init__(
        self, session: Session, harness: ChatHarness, daily_ai_limit: int
    ) -> None:
        self._session = session
        self._repository = ConversationRepository(session)
        self._ai_usage = AiUsage(session, harness, daily_ai_limit)
        self._harness = harness

    def get_help(self, request: HelpRequestIn) -> HelpResponse:
        conversation = self._repository.get_conversation(request.conversation_id)
        if conversation is None:
            raise conversation_not_found()
        if conversation.status == "finished":
            raise conversation_finished()
        self._ai_usage.ensure_within_daily_limit(conversation.profile.timezone)

        mode = help_mode_for(request.level, request.intent_vi)
        history = self._repository.list_recent_turns(
            conversation.id, limit=MAX_HISTORY_MESSAGES
        )
        context = HelpContext(
            level=conversation.level,
            topic=conversation.topic,
            summary=conversation.summary,
            history=[ChatTurn(role=m.role, text=m.original_text) for m in history],
            mode=mode,
            intent_vi=request.intent_vi,
        )
        try:
            result: TaskResult | None = self._harness.run_help(context)
        except Exception:
            logger.exception(
                "Unexpected error in help: conversation_id=%d", conversation.id
            )
            result = None

        reply: HelpReply | None = None
        error: ErrorBody | None = None
        if result is None:
            error = ProviderError("ai_unavailable").to_error_body()
        elif result.status == "succeeded":
            reply = result.value
        else:
            error = result.error
        try:
            # Kept so the learner can look back at which help they used (never a penalty).
            self._repository.add_help_request(
                conversation_id=conversation.id,
                mode=mode,
                intent_vi=request.intent_vi,
                hint_en=reply.hint_en if reply else None,
                explanation_vi=reply.explanation_vi if reply else None,
                status="succeeded" if reply else "failed",
            )
            self._ai_usage.record(
                operation="help",
                request_id=None,
                prompt_version=HELP_PROMPT_VERSION,
                error=error,
                call_count=result.attempts if result is not None else 1,
                duration_ms=result.duration_ms if result is not None else 0,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        if reply is None:
            return HelpResponse(status="failed", mode=mode, error=error)
        return HelpResponse(
            status="succeeded",
            mode=mode,
            hint_en=reply.hint_en,
            words=reply.words,
            explanation_vi=reply.explanation_vi,
        )
