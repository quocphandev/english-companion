"""HTTP layer for flashcard review (FR07)."""

from fastapi import APIRouter, status

from app.dependencies import ReviewServiceDep
from app.schemas.review import Flashcard, ReviewIn, ReviewOut

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/deck")
def get_deck(service: ReviewServiceDep) -> list[Flashcard]:
    return service.deck()


@router.post("", status_code=status.HTTP_201_CREATED)
def record_review(body: ReviewIn, service: ReviewServiceDep) -> ReviewOut:
    return service.record(body)
