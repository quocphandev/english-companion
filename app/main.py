"""FastAPI application entry point."""

from fastapi import FastAPI

from app.errors import register_error_handlers
from app.routers import conversations

app = FastAPI(title="English Companion")
register_error_handlers(app)
app.include_router(conversations.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: confirms the server is running."""
    return {"status": "ok"}
