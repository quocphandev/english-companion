"""HTTP layer for saved vocabulary (FR06)."""

from fastapi import APIRouter, Response, status

from app.dependencies import VocabularyServiceDep
from app.schemas.vocabulary import (
    ReviewStatus,
    SaveWordIn,
    SaveWordResponse,
    UpdateWordIn,
    WordOut,
)

router = APIRouter(prefix="/api/vocabulary", tags=["vocabulary"])


@router.get("")
def list_words(
    service: VocabularyServiceDep,
    q: str | None = None,
    status: ReviewStatus | None = None,
) -> list[WordOut]:
    return service.list_words(q, status)


@router.post("")
def save_word(
    body: SaveWordIn, service: VocabularyServiceDep, response: Response
) -> SaveWordResponse:
    result = service.save(body)
    response.status_code = (
        status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    )
    return result


@router.patch("/{word_id}")
def update_word(
    word_id: int, body: UpdateWordIn, service: VocabularyServiceDep
) -> WordOut:
    return service.update(word_id, body)


@router.delete("/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_word(word_id: int, service: VocabularyServiceDep) -> Response:
    service.delete(word_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
