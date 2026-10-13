"""HTML pages rendered on the server with Jinja2.

Jinja2 escapes every {{ value }} in .html templates, so user and AI text is
always shown as text, never run as HTML or script.
"""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.dependencies import (
    ConversationServiceDep,
    DataServiceDep,
    ReviewServiceDep,
    SummaryServiceDep,
    VocabularyServiceDep,
    get_allow_delete,
)
from app.schemas.conversation import MAX_MESSAGE_CHARS
from app.schemas.help import MAX_INTENT_CHARS
from app.services.data_service import DELETE_ALL_CONFIRMATION

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Second line of defence against XSS: the browser only runs scripts and styles
# served from this app, never inline code or code from other sites.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; object-src 'none'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}

router = APIRouter(include_in_schema=False)

AllowDeleteDep = Annotated[bool, Depends(get_allow_delete)]


def render(
    request: Request,
    template: str,
    context: dict[str, Any],
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template,
        context,
        status_code=status_code,
        headers=SECURITY_HEADERS,
    )


@router.get("/")
def home(request: Request, service: ConversationServiceDep) -> Response:
    """Open the latest conversation, or show the welcome screen if there is none."""
    conversations = service.list_conversations()
    if conversations:
        return RedirectResponse(
            f"/conversations/{conversations[0].id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return render(request, "chat.html", {"conversations": [], "conversation": None})


@router.get("/conversations/{conversation_id}")
def conversation_page(
    request: Request,
    conversation_id: int,
    service: ConversationServiceDep,
    summaries: SummaryServiceDep,
    allow_delete: AllowDeleteDep,
) -> HTMLResponse:
    history = service.get_history(conversation_id)
    if history is None:
        return render(request, "not_found.html", {}, status.HTTP_404_NOT_FOUND)
    return render(
        request,
        "chat.html",
        {
            "conversations": service.list_conversations(),
            "conversation": history,
            "summary": summaries.summary_of(conversation_id),
            "ai_provider": get_settings().ai_provider,
            "max_message_chars": MAX_MESSAGE_CHARS,
            "max_intent_chars": MAX_INTENT_CHARS,
            "allow_delete": allow_delete,
        },
    )


@router.get("/vocabulary")
def vocabulary_page(
    request: Request,
    conversations: ConversationServiceDep,
    vocabulary: VocabularyServiceDep,
    q: str | None = None,
    status: str | None = None,
) -> HTMLResponse:
    """FR06: saved words, newest first, with search and a reviewed/unreviewed filter."""
    query = (q or "").strip()[:100]
    review_status = status if status in ("reviewed", "unreviewed") else None
    return render(
        request,
        "vocabulary.html",
        {
            "conversations": conversations.list_conversations(),
            "conversation": None,
            "active_page": "vocabulary",
            "words": vocabulary.list_words(query or None, review_status),
            "query": query,
            "review_status": review_status or "",
        },
    )


@router.get("/review")
def review_page(
    request: Request, conversations: ConversationServiceDep, reviews: ReviewServiceDep
) -> HTMLResponse:
    """FR07 (MVP): manual flashcards."""
    return render(
        request,
        "review.html",
        {
            "conversations": conversations.list_conversations(),
            "conversation": None,
            "active_page": "review",
            "cards": reviews.deck(),
        },
    )


@router.get("/settings")
def settings_page(
    request: Request,
    conversations: ConversationServiceDep,
    data: DataServiceDep,
    allow_delete: AllowDeleteDep,
) -> HTMLResponse:
    """AI provider info, today's usage and "delete all learning data"."""
    settings = get_settings()
    return render(
        request,
        "settings.html",
        {
            "conversations": conversations.list_conversations(),
            "conversation": None,
            "active_page": "settings",
            "ai_provider": settings.ai_provider,
            "ai_model": settings.gemini_model
            if settings.ai_provider == "gemini"
            else "",
            "calls_today": data.calls_today(),
            "daily_limit": settings.daily_ai_limit,
            "delete_confirmation": DELETE_ALL_CONFIRMATION,
            "allow_delete": allow_delete,
        },
    )
