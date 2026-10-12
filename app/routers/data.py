"""HTTP layer for deleting learning data and flagging chatbot replies."""

from fastapi import APIRouter, Response, status

from app.dependencies import DataServiceDep
from app.schemas.data import DeleteAllIn, ReviewFlagIn, ReviewFlagOut

router = APIRouter(prefix="/api", tags=["data"])


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_conversation(conversation_id: int, service: DataServiceDep) -> Response:
    service.delete_conversation(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/data/delete-all", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_learning_data(body: DeleteAllIn, service: DataServiceDep) -> Response:
    service.delete_all(body.confirm)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/messages/{message_id}/review-flag")
def flag_reply(
    message_id: int, body: ReviewFlagIn, service: DataServiceDep
) -> ReviewFlagOut:
    flagged = service.set_needs_review(message_id, body.needs_review)
    return ReviewFlagOut(message_id=message_id, needs_review=flagged)
