from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

HELP_MODES = ("words", "starter", "sample", "intent")


class HelpRequest(Base):
    """One "Giúp tôi" use (FR03), kept so the learner can look back; never a penalty."""

    __tablename__ = "help_requests"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('words', 'starter', 'sample', 'intent')", name="mode"
        ),
        CheckConstraint("status IN ('succeeded', 'failed')", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[str] = mapped_column(String(20))
    intent_vi: Mapped[str | None] = mapped_column(Text)
    hint_en: Mapped[str | None] = mapped_column(Text)
    explanation_vi: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
