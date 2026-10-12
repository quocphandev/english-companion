from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.profile import Profile


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'finished')", name="status"),
        CheckConstraint("level IN ('A1', 'A2', 'B1', 'B2')", name="level"),
        CheckConstraint(
            "correction_mode IN ('learning', 'conversation')", name="correction_mode"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    topic: Mapped[str] = mapped_column(String(100))
    # Settings chosen when the conversation started; they stay with this conversation.
    level: Mapped[str] = mapped_column(String(2), server_default="A2")
    correction_mode: Mapped[str] = mapped_column(String(20), server_default="learning")
    status: Mapped[str] = mapped_column(String(20), server_default="active")
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    profile: Mapped["Profile"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        order_by="Message.created_at",
        passive_deletes=True,
    )
