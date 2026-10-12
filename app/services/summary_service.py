"""FR10: finish a session and build its summary.

Mistakes and saved words come from the database; the AI only writes the recap
and the next exercise, and may only add key words that really appear in the
conversation. If the AI fails, the session still ends and the summary still
lists mistakes and words.
"""

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.errors import AppError, conversation_not_found
from app.harness.chat_harness import ChatHarness, TaskResult
from app.harness.context import ChatTurn
from app.harness.prompts import SUMMARY_PROMPT_VERSION
from app.harness.summary_context import SummaryContext
from app.models import Conversation, Correction, Vocabulary
from app.providers.errors import ProviderError
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.vocabulary_repository import VocabularyRepository
from app.schemas.ai import SummaryReply, SummaryWord
from app.schemas.error import ErrorBody
from app.schemas.summary import SessionSummary, SummaryError, SummaryWordOut
from app.services.ai_usage import AiUsage

logger = logging.getLogger(__name__)

MAX_SUMMARY_ERRORS = 5
MAX_SUMMARY_WORDS = 5


def pick_errors(
    corrections: list[Correction], limit: int = MAX_SUMMARY_ERRORS
) -> list[SummaryError]:
    """Real mistakes only (no style tips), each fix listed once, at most `limit`."""
    seen: set[tuple[str, str]] = set()
    picked: list[SummaryError] = []
    for item in corrections:
        if item.category == "naturalness":
            continue
        key = (item.original_span.lower(), item.corrected_text.lower())
        if key in seen:
            continue
        seen.add(key)
        picked.append(
            SummaryError(
                category=item.category,
                original_span=item.original_span,
                corrected_text=item.corrected_text,
                explanation_vi=item.explanation_vi,
            )
        )
        if len(picked) == limit:
            break
    return picked


def pick_words(
    saved: list[Vocabulary],
    ai_words: list[SummaryWord],
    conversation_text: str,
    limit: int = MAX_SUMMARY_WORDS,
) -> list[SummaryWordOut]:
    """Saved words first; AI words only if they really occur in the conversation."""
    text = conversation_text.lower()
    seen: set[str] = set()
    picked: list[SummaryWordOut] = []
    candidates = [(w.selected_text, w.meaning_vi, True) for w in saved] + [
        (w.text, w.meaning_vi, False) for w in ai_words if w.text.lower() in text
    ]
    for word, meaning, is_saved in candidates:
        if word.lower() in seen:
            continue
        seen.add(word.lower())
        picked.append(SummaryWordOut(text=word, meaning_vi=meaning, saved=is_saved))
        if len(picked) == limit:
            break
    return picked


class SummaryService:
    def __init__(
        self, session: Session, harness: ChatHarness, daily_ai_limit: int
    ) -> None:
        self._session = session
        self._conversations = ConversationRepository(session)
        self._words = VocabularyRepository(session)
        self._ai_usage = AiUsage(session, harness, daily_ai_limit)
        self._harness = harness

    def finish(self, conversation_id: int) -> SessionSummary:
        conversation = self._conversations.get_conversation(conversation_id)
        if conversation is None:
            raise conversation_not_found()
        if conversation.status == "finished":
            return self.build(conversation)  # finishing twice never calls the AI again

        reply, ai_error = self._ask_ai(conversation)
        conversation.status = "finished"
        conversation.finished_at = func.now()
        details: dict[str, object] = {}
        if reply is not None:
            conversation.summary = reply.recap_vi
            details = {
                "next_exercise_vi": reply.next_exercise_vi,
                "key_words": [w.model_dump() for w in reply.key_words],
            }
        if ai_error is not None:
            details["ai_error"] = ai_error.model_dump()
        conversation.summary_details = details
        self._session.commit()
        self._session.refresh(conversation)
        logger.info(
            "Conversation finished: id=%d ai=%s",
            conversation.id,
            "ok" if reply else (ai_error.code if ai_error else "skipped"),
        )
        return self.build(conversation)

    def summary_of(self, conversation_id: int) -> SessionSummary | None:
        """The stored summary of a finished conversation (None while it is active)."""
        conversation = self._conversations.get_conversation(conversation_id)
        if conversation is None or conversation.status != "finished":
            return None
        return self.build(conversation)

    def build(self, conversation: Conversation) -> SessionSummary:
        details = conversation.summary_details or {}
        messages = self._conversations.list_messages(conversation.id)
        conversation_text = "\n".join(m.original_text for m in messages)
        ai_words = [SummaryWord.model_validate(w) for w in details.get("key_words", [])]
        ai_error = details.get("ai_error")
        return SessionSummary(
            conversation_id=conversation.id,
            finished_at=conversation.finished_at,
            recap_vi=conversation.summary,
            next_exercise_vi=details.get("next_exercise_vi"),
            errors=pick_errors(self._conversations.list_corrections(conversation.id)),
            words=pick_words(
                self._words.words_from_conversation(conversation.id),
                ai_words,
                conversation_text,
            ),
            help_count=self._conversations.count_help_requests(conversation.id),
            ai_error=ErrorBody.model_validate(ai_error) if ai_error else None,
        )

    def _ask_ai(
        self, conversation: Conversation
    ) -> tuple[SummaryReply | None, ErrorBody | None]:
        """Recap + next exercise from the AI. Never blocks finishing the session."""
        messages = self._conversations.list_messages(conversation.id)
        if not any(m.role == "user" for m in messages):
            return None, None  # nothing was said: no AI call
        try:
            self._ai_usage.ensure_within_daily_limit(conversation.profile.timezone)
        except AppError as error:
            return None, error.body
        context = SummaryContext(
            topic=conversation.topic,
            turns=[
                ChatTurn(role=m.role, text=m.original_text)
                for m in messages
                if m.status == "succeeded"
            ],
            mistakes=[
                f'"{e.original_span}" -> "{e.corrected_text}" ({e.category})'
                for e in pick_errors(
                    self._conversations.list_corrections(conversation.id)
                )
            ],
        )
        try:
            result: TaskResult | None = self._harness.run_summary(context)
        except Exception:
            logger.exception(
                "Unexpected error in summary: conversation_id=%d", conversation.id
            )
            result = None
        if result is None:
            error = ProviderError("ai_unavailable").to_error_body()
        elif result.status == "succeeded":
            error = None
        else:
            error = result.error
        self._ai_usage.record(
            operation="summary",
            request_id=None,
            prompt_version=SUMMARY_PROMPT_VERSION,
            error=error,
            call_count=result.attempts if result is not None else 1,
            duration_ms=result.duration_ms if result is not None else 0,
        )
        return (result.value if error is None and result else None), error
