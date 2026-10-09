"""Request and response bodies for the conversation API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from app.schemas.error import ErrorBody

MAX_MESSAGE_CHARS = 2000
# Client-generated id, e.g. a UUID. Reused when the client retries the same message.
REQUEST_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class CreateConversationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str = Field(min_length=1, max_length=100)
    level: Literal["A1", "A2", "B1", "B2"] = "A2"
    correction_mode: Literal["learning", "conversation"] = "learning"


class CreateConversationResponse(BaseModel):
    conversation_id: int


class SendMessageRequest(BaseModel):
    request_id: str = Field(pattern=REQUEST_ID_PATTERN)
    text: str
    input_mode: Literal["text", "voice"] = "text"

    @field_validator("text")
    @classmethod
    def check_text(cls, value: str) -> str:
        """Reject blank or too long text, but keep the original (unstripped) value."""
        if not value.strip():
            raise PydanticCustomError("empty_message", "Message must not be empty")
        if len(value) > MAX_MESSAGE_CHARS:
            raise PydanticCustomError(
                "message_too_long",
                "Message must be at most {max_chars} characters",
                {"max_chars": MAX_MESSAGE_CHARS},
            )
        return value


class MessageOut(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    text: str
    status: Literal["pending", "succeeded", "failed"]
    created_at: datetime


class CorrectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    original_span: str
    corrected_text: str
    explanation_vi: str


class SendMessageResponse(BaseModel):
    status: Literal["pending", "succeeded", "failed"]
    message: MessageOut
    reply: MessageOut | None = None
    corrections: list[CorrectionOut] = []
    error: ErrorBody | None = None
