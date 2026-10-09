from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AiRun(Base):
    """One AI task (a chat turn or an eval sentence): metadata only, never content.

    Used to enforce DAILY_AI_LIMIT and to see how the AI behaves over time.
    """

    __tablename__ = "ai_runs"
    __table_args__ = (
        CheckConstraint("operation IN ('chat_turn', 'eval')", name="operation"),
        CheckConstraint("status IN ('succeeded', 'failed')", name="status"),
        CheckConstraint("call_count >= 0", name="call_count"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Not unique: retrying a failed turn reuses its request_id.
    request_id: Mapped[str | None] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(50))
    # Provider calls made for this task (a JSON repair makes it 2).
    call_count: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
