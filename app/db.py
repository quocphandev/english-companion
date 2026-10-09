"""Database engine and session factory (synchronous SQLAlchemy)."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def create_db_engine(url: str, **kwargs: Any) -> Engine:
    """Create an engine whose connections always use the UTC time zone."""
    return create_engine(
        url,
        pool_pre_ping=True,
        # Fail fast instead of hanging when the database is unreachable.
        connect_args={"options": "-c timezone=UTC", "connect_timeout": 10},
        **kwargs,
    )


@lru_cache
def get_engine() -> Engine:
    """Return the application engine, created once from DATABASE_URL."""
    return create_db_engine(get_settings().database_url)


SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yield one session per request, then close it."""
    with SessionLocal(bind=get_engine()) as session:
        yield session
