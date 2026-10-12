"""Bodies for data controls: delete all, flag a reply."""

from pydantic import BaseModel, Field


class DeleteAllIn(BaseModel):
    # The learner must type the confirmation phrase shown on the settings page.
    confirm: str = Field(max_length=50)


class ReviewFlagIn(BaseModel):
    needs_review: bool


class ReviewFlagOut(BaseModel):
    message_id: int
    needs_review: bool
