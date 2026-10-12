"""Request and response bodies for saved vocabulary (FR06)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SaveWordIn(BaseModel):
    """Save what was looked up. The server re-reads the sentence and the cached
    lookup itself; only the (possibly edited) meaning comes from the learner."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: int
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    meaning_vi: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def end_after_start(self) -> "SaveWordIn":
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class UpdateWordIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    note: str | None = Field(default=None, max_length=1000)
    meaning_vi: str | None = Field(default=None, min_length=1, max_length=300)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_sentence: str
    selected_start: int
    selected_end: int


class WordOut(BaseModel):
    id: int
    lemma: str
    selected_text: str
    meaning_vi: str
    pos: str
    example_en: str
    note: str | None
    created_at: datetime
    sources: list[SourceOut]


class SaveWordResponse(BaseModel):
    # False when the same word with the same meaning already existed (a source was added).
    created: bool
    word: WordOut
