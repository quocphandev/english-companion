"""Request and response bodies for "Giúp tôi" (FR03)."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.ai import HelpWord
from app.schemas.error import ErrorBody

MAX_INTENT_CHARS = 500


class HelpRequestIn(BaseModel):
    conversation_id: int
    # 1: words, 2: sentence starter, 3: sample sentence.
    level: Literal[1, 2, 3] = 1
    # What the learner wants to say, in Vietnamese. Blank means "not given".
    intent_vi: str | None = Field(default=None, max_length=MAX_INTENT_CHARS)

    @field_validator("intent_vi")
    @classmethod
    def blank_intent_is_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class HelpResponse(BaseModel):
    """A suggestion to edit and send yourself; it is never sent automatically."""

    status: Literal["succeeded", "failed"]
    mode: Literal["words", "starter", "sample", "intent"]
    hint_en: str | None = None
    words: list[HelpWord] = []
    explanation_vi: str | None = None
    error: ErrorBody | None = None
