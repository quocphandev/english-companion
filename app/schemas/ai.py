"""Schemas for structured output returned by the AI for a chat turn."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CorrectionCategory = Literal["grammar", "word_choice", "spelling", "naturalness"]


class Correction(BaseModel):
    """One issue in the learner's message. "naturalness" is an optional style tip."""

    model_config = ConfigDict(str_strip_whitespace=True)

    category: CorrectionCategory
    original_span: str = Field(min_length=1)
    corrected_text: str = Field(min_length=1)
    explanation_vi: str = Field(min_length=1)


class SuggestedWord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1)
    meaning_vi: str = Field(min_length=1)


class TurnReply(BaseModel):
    """What the AI must return for one turn. Unknown extra fields are ignored."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    reply_en: str = Field(min_length=1)
    corrections: list[Correction] = Field(default_factory=list, max_length=3)
    suggested_words: list[SuggestedWord] = Field(default_factory=list, max_length=3)
