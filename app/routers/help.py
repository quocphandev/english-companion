"""HTTP layer for "Giúp tôi" (FR03)."""

from fastapi import APIRouter

from app.dependencies import HelpServiceDep
from app.schemas.help import HelpRequestIn, HelpResponse

router = APIRouter(prefix="/api", tags=["help"])


@router.post("/help")
def get_help(body: HelpRequestIn, service: HelpServiceDep) -> HelpResponse:
    return service.get_help(body)
