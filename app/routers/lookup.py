"""HTTP layer for contextual lookup (FR05)."""

from fastapi import APIRouter

from app.dependencies import LookupServiceDep
from app.schemas.lookup import LookupRequestIn, LookupResponse

router = APIRouter(prefix="/api", tags=["lookup"])


@router.post("/lookup")
def lookup(body: LookupRequestIn, service: LookupServiceDep) -> LookupResponse:
    return service.lookup(body)
