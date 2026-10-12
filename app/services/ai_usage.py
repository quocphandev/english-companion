"""Shared AI bookkeeping for services: the daily limit check and ai_runs records."""

import logging

from sqlalchemy.orm import Session

from app.errors import daily_limit_reached
from app.harness.chat_harness import ChatHarness
from app.repositories.ai_run_repository import AiRunRepository
from app.schemas.error import ErrorBody

logger = logging.getLogger(__name__)


class AiUsage:
    def __init__(
        self, session: Session, harness: ChatHarness, daily_ai_limit: int
    ) -> None:
        self._runs = AiRunRepository(session)
        self._harness = harness
        self._daily_ai_limit = daily_ai_limit

    def ensure_within_daily_limit(self, timezone: str) -> None:
        """Refuse before saving or calling the AI when DAILY_AI_LIMIT is used up."""
        if self._harness.provider_name == "fake":
            return  # offline and free: never limited
        used = self._runs.count_calls_today(timezone)
        if used >= self._daily_ai_limit:
            logger.info(
                "Daily AI limit reached: used=%d limit=%d", used, self._daily_ai_limit
            )
            raise daily_limit_reached(self._daily_ai_limit)

    def record(
        self,
        *,
        operation: str,
        request_id: str | None,
        prompt_version: str,
        error: ErrorBody | None,
        call_count: int,
        duration_ms: int,
    ) -> None:
        """Add one ai_runs row (metadata only). Commit is the caller's job."""
        self._runs.add_run(
            operation=operation,
            request_id=request_id,
            provider=self._harness.provider_name,
            model=self._harness.model_name,
            prompt_version=prompt_version,
            status="succeeded" if error is None else "failed",
            error_code=error.code if error else None,
            call_count=call_count,
            duration_ms=duration_ms,
        )
