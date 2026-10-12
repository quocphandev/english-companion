from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReviewEvent(Base):
    """One flashcard answer (FR07): the learner remembered the word or not."""

    __tablename__ = "review_events"
    __table_args__ = (
        CheckConstraint("outcome IN ('remembered', 'again')", name="outcome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary.id", ondelete="CASCADE"), index=True
    )
    outcome: Mapped[str] = mapped_column(String(20))
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
