"""Bodies for manual flashcard review (FR07)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Outcome = Literal["remembered", "again"]


class ReviewIn(BaseModel):
    vocabulary_id: int
    outcome: Outcome


class ReviewOut(BaseModel):
    vocabulary_id: int
    outcome: Outcome
    reviewed_at: datetime


class Flashcard(BaseModel):
    """Front: the word and a sentence with the word blanked. Back: meaning and example."""

    id: int
    lemma: str
    selected_text: str
    pos: str
    meaning_vi: str
    example_en: str
    cloze: str | None
    last_outcome: Outcome | None
