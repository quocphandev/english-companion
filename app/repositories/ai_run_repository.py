"""Queries for ai_runs: record AI tasks and count today's calls for DAILY_AI_LIMIT."""

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models import AiRun

# The offline fake provider is free, so it never counts toward the daily limit.
UNCOUNTED_PROVIDERS = ("fake",)


class AiRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_run(
        self,
        *,
        operation: str,
        request_id: str | None,
        provider: str,
        model: str,
        prompt_version: str,
        status: str,
        error_code: str | None,
        call_count: int,
        duration_ms: int,
    ) -> AiRun:
        run = AiRun(
            operation=operation,
            request_id=request_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            status=status,
            error_code=error_code,
            call_count=call_count,
            duration_ms=duration_ms,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def count_calls_today(self, timezone: str) -> int:
        """Provider calls made today, where "today" is the calendar day in `timezone`.

        Postgres converts the time zone itself (timezone(zone, timestamptz)),
        so no time zone database is needed in Python.
        """
        local_day = cast(func.timezone(timezone, AiRun.created_at), Date)
        today = cast(func.timezone(timezone, func.now()), Date)
        total = self._session.scalar(
            select(func.coalesce(func.sum(AiRun.call_count), 0)).where(
                AiRun.provider.not_in(UNCOUNTED_PROVIDERS),
                local_day == today,
            )
        )
        return int(total or 0)
