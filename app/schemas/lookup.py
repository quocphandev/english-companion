"""Request and response bodies for contextual lookup (FR05)."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.ai import LookupAlternative
from app.schemas.error import ErrorBody


class LookupRequestIn(BaseModel):
    """A selection inside one message, as Unicode code point offsets [start, end)."""

    message_id: int
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def end_after_start(self) -> "LookupRequestIn":
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class LookupResponse(BaseModel):
    status: Literal["succeeded", "failed"]
    selected_text: str
    source_sentence: str
    # Offsets of the selection inside source_sentence (needed to save the word later).
    sentence_start: int
    sentence_end: int
    cached: bool = False
    lemma: str | None = None
    pos: str | None = None
    meaning_vi: str | None = None
    example_en: str | None = None
    sentence_meaning_vi: str | None = None
    alternatives: list[LookupAlternative] = []
    uncertainty_vi: str | None = None
    error: ErrorBody | None = None
