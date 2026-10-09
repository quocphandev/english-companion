from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("level IN ('A1', 'A2', 'B1', 'B2')", name="level"),
        CheckConstraint(
            "correction_mode IN ('learning', 'conversation')", name="correction_mode"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(2), server_default="A2")
    correction_mode: Mapped[str] = mapped_column(String(20), server_default="learning")
    timezone: Mapped[str] = mapped_column(String(64), server_default="Asia/Ho_Chi_Minh")
    reuse_words: Mapped[bool] = mapped_column(server_default=text("true"))

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="profile", passive_deletes=True
    )
