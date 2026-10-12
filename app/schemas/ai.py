"""Schemas for structured output returned by the AI (chat turn, help, ...)."""

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


class HelpWord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1)
    meaning_vi: str = Field(min_length=1)


class HelpReply(BaseModel):
    """Help when the learner is stuck (FR03). `hint_en` is what "Chèn vào ô nhập" inserts."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    hint_en: str = Field(min_length=1, max_length=400)
    words: list[HelpWord] = Field(default_factory=list, max_length=3)
    explanation_vi: str = Field(min_length=1)


class LookupAlternative(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    meaning_vi: str = Field(min_length=1)
    note_vi: str = Field(min_length=1)


class LookupReply(BaseModel):
    """Meaning of a selected word or phrase in its sentence (FR05)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    lemma: str = Field(min_length=1)
    pos: str = Field(min_length=1)
    meaning_vi: str = Field(min_length=1)
    example_en: str = Field(min_length=1)
    sentence_meaning_vi: str | None = None
    # Filled only when the context allows several readings.
    alternatives: list[LookupAlternative] = Field(default_factory=list, max_length=3)
    uncertainty_vi: str | None = None
