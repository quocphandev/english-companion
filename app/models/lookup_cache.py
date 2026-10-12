from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LookupCache(Base):
    """A lookup result, reused only for the same sentence, selection, language and prompt."""

    __tablename__ = "lookup_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    # sha256 of (prompt_version, language, sentence, start, end): never the bare word.
    cache_key: Mapped[str] = mapped_column(String(64), unique=True)
    prompt_version: Mapped[str] = mapped_column(String(50))
    source_sentence: Mapped[str] = mapped_column(Text)
    selected_text: Mapped[str] = mapped_column(Text)
    selection_start: Mapped[int] = mapped_column(Integer)
    selection_end: Mapped[int] = mapped_column(Integer)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
