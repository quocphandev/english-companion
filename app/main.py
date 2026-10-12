"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from app.errors import register_error_handlers
from app.routers import conversations, help, lookup, pages

STATIC_DIR = Path(__file__).resolve().parent / "static"


class RevalidatedStaticFiles(StaticFiles):
    """Static files the browser must re-check (cheap 304) so new JS/CSS shows at once.

    Without Cache-Control, browsers may keep an old file for a while after an update.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app = FastAPI(title="English Companion")
register_error_handlers(app)
app.mount("/static", RevalidatedStaticFiles(directory=STATIC_DIR), name="static")
app.include_router(conversations.router)
app.include_router(help.router)
app.include_router(lookup.router)
app.include_router(pages.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: confirms the server is running."""
    return {"status": "ok"}
