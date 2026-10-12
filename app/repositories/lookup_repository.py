"""Queries for the lookup cache (FR05)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import LookupCache, Message


class LookupRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_message(self, message_id: int) -> Message | None:
        return self._session.get(Message, message_id)

    def find_cached(self, cache_key: str) -> LookupCache | None:
        return self._session.scalar(
            select(LookupCache).where(LookupCache.cache_key == cache_key)
        )

    def save(
        self,
        *,
        cache_key: str,
        prompt_version: str,
        source_sentence: str,
        selected_text: str,
        selection_start: int,
        selection_end: int,
        result: dict[str, Any],
    ) -> None:
        """Insert once; a concurrent identical lookup keeps the first result."""
        statement = (
            insert(LookupCache)
            .values(
                cache_key=cache_key,
                prompt_version=prompt_version,
                source_sentence=source_sentence,
                selected_text=selected_text,
                selection_start=selection_start,
                selection_end=selection_end,
                result=result,
            )
            .on_conflict_do_nothing(index_elements=["cache_key"])
        )
        self._session.execute(statement)
