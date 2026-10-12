from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Vocabulary(Base):
    """A saved word or phrase with one meaning (FR06).

    Unique per (profile, lemma, normalized meaning): saving the same word with
    the same meaning again only adds a source sentence.
    """

    __tablename__ = "vocabulary"
    __table_args__ = (UniqueConstraint("profile_id", "lemma", "meaning_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    # Base form, normalized to lower case ("look after").
    lemma: Mapped[str] = mapped_column(String(100))
    # What the learner selected the first time ("looks after").
    selected_text: Mapped[str] = mapped_column(String(200))
    meaning_vi: Mapped[str] = mapped_column(Text)
    # meaning_vi normalized (case, spaces, punctuation) for duplicate detection.
    meaning_key: Mapped[str] = mapped_column(String(300))
    pos: Mapped[str] = mapped_column(String(40))
    example_en: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    # Reserved for the spaced-review schedule of phase 3.
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sources: Mapped[list["VocabularySource"]] = relationship(
        back_populates="vocabulary",
        order_by="VocabularySource.id",
        passive_deletes=True,
    )


class VocabularySource(Base):
    """A sentence where a saved word was met. Deleted with its message; the word stays."""

    __tablename__ = "vocabulary_sources"
    __table_args__ = (
        UniqueConstraint(
            "vocabulary_id", "message_id", "selected_start", "selected_end"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    source_sentence: Mapped[str] = mapped_column(Text)
    # Code point offsets of the selection inside source_sentence.
    selected_start: Mapped[int] = mapped_column(Integer)
    selected_end: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    vocabulary: Mapped[Vocabulary] = relationship(back_populates="sources")
