"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(title="English Companion")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: confirms the server is running."""
    return {"status": "ok"}
