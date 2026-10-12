"""End-of-session summary (FR10)."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.error import ErrorBody


class SummaryError(BaseModel):
    category: str
    original_span: str
    corrected_text: str
    explanation_vi: str


class SummaryWordOut(BaseModel):
    text: str
    meaning_vi: str
    # True for words the learner saved; False for words the AI picked from the session.
    saved: bool


class SessionSummary(BaseModel):
    """Errors and words come from the database, so nothing is invented.
    recap_vi / next_exercise_vi come from the AI and may be missing if it failed."""

    conversation_id: int
    finished_at: datetime | None
    recap_vi: str | None = None
    next_exercise_vi: str | None = None
    errors: list[SummaryError] = []
    words: list[SummaryWordOut] = []
    help_count: int = 0
    ai_error: ErrorBody | None = None
