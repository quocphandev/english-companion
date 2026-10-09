from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="role"),
        CheckConstraint("input_mode IN ('text', 'voice')", name="input_mode"),
        CheckConstraint("status IN ('pending', 'succeeded', 'failed')", name="status"),
        Index(
            "ix_messages_conversation_id_created_at", "conversation_id", "created_at"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))
    original_text: Mapped[str] = mapped_column(Text)
    input_mode: Mapped[str] = mapped_column(String(10), server_default="text")
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    # Set on user turns so a resend with the same id cannot create a duplicate.
    # NULL for assistant replies; Postgres allows many NULLs in a unique column.
    request_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
