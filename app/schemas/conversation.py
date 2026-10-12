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
    needs_review: bool = False


class CorrectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    original_span: str
    corrected_text: str
    explanation_vi: str


class Segment(BaseModel):
    """A piece of a sentence; `changed` marks the part a correction touches."""

    text: str
    changed: bool = False


class CorrectionView(BaseModel):
    """Everything the correction card shows for one learner message."""

    original: list[Segment]
    # The sentence with real errors fixed; None when no span could be located.
    corrected: list[Segment] | None = None
    errors: list[CorrectionOut]
    # "naturalness" items: optional style tips, shown apart from real errors.
    suggestions: list[CorrectionOut]


class ConversationSummary(BaseModel):
    id: int
    topic: str
    created_at: datetime
    status: Literal["active", "finished"] = "active"


class TurnView(BaseModel):
    """One user message with its reply and corrections, as shown in the chat."""

    message: MessageOut
    reply: MessageOut | None = None
    corrections: list[CorrectionOut] = []
    correction_view: CorrectionView | None = None


class ConversationHistory(BaseModel):
    id: int
    topic: str
    level: Literal["A1", "A2", "B1", "B2"]
    correction_mode: Literal["learning", "conversation"]
    status: Literal["active", "finished"] = "active"
    # The chatbot's opening question (FR01), shown before the first turn.
    opener: MessageOut | None = None
    turns: list[TurnView]


class SendMessageResponse(BaseModel):
    status: Literal["pending", "succeeded", "failed"]
    message: MessageOut
    reply: MessageOut | None = None
    corrections: list[CorrectionOut] = []
    correction_view: CorrectionView | None = None
    error: ErrorBody | None = None
