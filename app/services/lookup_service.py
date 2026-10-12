"""FR05: meaning of a word or phrase in its sentence, cached per sentence + selection."""

import logging

from fastapi import status
from sqlalchemy.orm import Session

from app.errors import AppError
from app.harness.chat_harness import ChatHarness, TaskResult
from app.harness.lookup_context import LookupContext, lookup_cache_key
from app.harness.prompts import LOOKUP_PROMPT_VERSION
from app.providers.errors import ProviderError
from app.repositories.lookup_repository import LookupRepository
from app.schemas.ai import LookupReply
from app.schemas.error import ErrorBody
from app.schemas.lookup import LookupRequestIn, LookupResponse
from app.services.ai_usage import AiUsage
from app.services.text_selection import MAX_SELECTION_WORDS, sentence_bounds, words_in

logger = logging.getLogger(__name__)


def message_not_found() -> AppError:
    return AppError(
        "message_not_found",
        "Không tìm thấy tin nhắn.",
        http_status=status.HTTP_404_NOT_FOUND,
    )


def invalid_selection() -> AppError:
    return AppError(
        "invalid_selection",
        "Vùng chọn không hợp lệ. Hãy chọn một từ hoặc cụm từ trong tin nhắn.",
        http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


def selection_too_long() -> AppError:
    return AppError(
        "selection_too_long",
        f"Chỉ tra được tối đa {MAX_SELECTION_WORDS} từ liên tiếp.",
        http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


class LookupService:
    def __init__(
        self, session: Session, harness: ChatHarness, daily_ai_limit: int
    ) -> None:
        self._session = session
        self._repository = LookupRepository(session)
        self._ai_usage = AiUsage(session, harness, daily_ai_limit)
        self._harness = harness

    def lookup(self, request: LookupRequestIn) -> LookupResponse:
        message = self._repository.get_message(request.message_id)
        if message is None:
            raise message_not_found()
        context = selection_context(message.original_text, request.start, request.end)

        cache_key = lookup_cache_key(context)
        cached = self._repository.find_cached(cache_key)
        if cached is not None:
            # Same sentence and selection: no AI call, nothing counted.
            return to_response(
                context, LookupReply.model_validate(cached.result), cached=True
            )

        timezone = message.conversation.profile.timezone
        self._ai_usage.ensure_within_daily_limit(timezone)
        try:
            result: TaskResult | None = self._harness.run_lookup(context)
        except Exception:
            logger.exception("Unexpected error in lookup: message_id=%d", message.id)
            result = None

        reply: LookupReply | None = None
        error: ErrorBody | None = None
        if result is None:
            error = ProviderError("ai_unavailable").to_error_body()
        elif result.status == "succeeded":
            reply = result.value
        else:
            error = result.error

        try:
            if reply is not None:
                self._repository.save(
                    cache_key=cache_key,
                    prompt_version=LOOKUP_PROMPT_VERSION,
                    source_sentence=context.sentence,
                    selected_text=context.selected_text,
                    selection_start=context.start,
                    selection_end=context.end,
                    result=reply.model_dump(),
                )
            self._ai_usage.record(
                operation="lookup",
                request_id=None,
                prompt_version=LOOKUP_PROMPT_VERSION,
                error=error,
                call_count=result.attempts if result is not None else 1,
                duration_ms=result.duration_ms if result is not None else 0,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        if reply is None:
            return LookupResponse(
                status="failed",
                selected_text=context.selected_text,
                source_sentence=context.sentence,
                sentence_start=context.start,
                sentence_end=context.end,
                error=error,
            )
        return to_response(context, reply, cached=False)


def selection_context(text: str, start: int, end: int) -> LookupContext:
    """Validate the selection and cut out its sentence (offsets become sentence-relative)."""
    if end > len(text) or not text[start:end].strip():
        raise invalid_selection()
    words = words_in(text, start, end)
    if not words:
        raise invalid_selection()
    if len(words) > MAX_SELECTION_WORDS:
        raise selection_too_long()
    # Snap to whole words: a click inside "booking" looks up "booking".
    start, end = words[0][0], words[-1][1]
    sentence_start, sentence_end = sentence_bounds(text, start, end)
    return LookupContext(
        sentence=text[sentence_start:sentence_end],
        start=start - sentence_start,
        end=end - sentence_start,
    )


def to_response(
    context: LookupContext, reply: LookupReply, *, cached: bool
) -> LookupResponse:
    return LookupResponse(
        status="succeeded",
        selected_text=context.selected_text,
        source_sentence=context.sentence,
        sentence_start=context.start,
        sentence_end=context.end,
        cached=cached,
        lemma=reply.lemma,
        pos=reply.pos,
        meaning_vi=reply.meaning_vi,
        example_en=reply.example_en,
        sentence_meaning_vi=reply.sentence_meaning_vi,
        alternatives=reply.alternatives,
        uncertainty_vi=reply.uncertainty_vi,
    )
