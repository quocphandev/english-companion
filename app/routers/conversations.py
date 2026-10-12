"""HTTP layer for conversations: parse input, call the service, return output.

Endpoints are plain `def` because the database layer is synchronous;
FastAPI runs them in a worker thread so the server is not blocked.
"""

from fastapi import APIRouter, status

from app.dependencies import ConversationServiceDep, SummaryServiceDep
from app.schemas.conversation import (
    CreateConversationRequest,
    CreateConversationResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.schemas.summary import SessionSummary

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: CreateConversationRequest, service: ConversationServiceDep
) -> CreateConversationResponse:
    conversation_id = service.create_conversation(body)
    return CreateConversationResponse(conversation_id=conversation_id)


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: int, body: SendMessageRequest, service: ConversationServiceDep
) -> SendMessageResponse:
    return service.send_message(conversation_id, body)


@router.post("/{conversation_id}/finish")
def finish_conversation(
    conversation_id: int, service: SummaryServiceDep
) -> SessionSummary:
    """FR10: end the session and return its summary (calling it again changes nothing)."""
    return service.finish(conversation_id)
