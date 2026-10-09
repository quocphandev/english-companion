"""HTML pages rendered on the server with Jinja2.

Jinja2 escapes every {{ value }} in .html templates, so user and AI text is
always shown as text, never run as HTML or script.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.dependencies import ConversationServiceDep
from app.schemas.conversation import MAX_MESSAGE_CHARS

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
    request: Request, conversation_id: int, service: ConversationServiceDep
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
            "max_message_chars": MAX_MESSAGE_CHARS,
        },
    )
