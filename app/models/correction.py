from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.message import Message


class Correction(Base):
    __tablename__ = "corrections"
    __table_args__ = (
        CheckConstraint(
            "category IN ('grammar', 'word_choice', 'spelling', 'naturalness')",
            name="category",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(20))
    original_span: Mapped[str] = mapped_column(Text)
    corrected_text: Mapped[str] = mapped_column(Text)
    explanation_vi: Mapped[str] = mapped_column(Text)
    # Which prompt produced this correction, to compare quality across versions.
    prompt_version: Mapped[str] = mapped_column(String(50))

    message: Mapped["Message"] = relationship(back_populates="corrections")
