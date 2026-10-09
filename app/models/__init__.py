"""Import every model here so Base.metadata knows all tables (needed by Alembic)."""

from app.models.base import Base
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.profile import Profile

__all__ = ["Base", "Conversation", "Message", "Profile"]
