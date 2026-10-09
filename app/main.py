"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.errors import register_error_handlers
from app.routers import conversations, pages

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="English Companion")
register_error_handlers(app)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(conversations.router)
app.include_router(pages.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: confirms the server is running."""
    return {"status": "ok"}
