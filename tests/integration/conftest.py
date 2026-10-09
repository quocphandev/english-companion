"""Shared fixtures for integration tests that need a real (test) database."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import create_db_engine, get_session
from app.dependencies import get_harness
from app.harness.chat_harness import ChatHarness
from app.main import app
from app.providers.ai_provider import AIProvider
from app.providers.fake_provider import FakeProvider

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Engine for TEST_DATABASE_URL, migrated to the latest schema once per run."""
    settings = get_settings()
    test_url = settings.test_database_url
    if not test_url:
        pytest.fail("TEST_DATABASE_URL is not set; integration tests need a test DB.")
    if test_url == settings.database_url:
        pytest.fail("TEST_DATABASE_URL must differ from DATABASE_URL.")

    alembic_config = Config(PROJECT_ROOT / "alembic.ini")
    # ConfigParser treats "%" as special, so escape it in case the password has one.
    alembic_config.set_main_option("sqlalchemy.url", test_url.replace("%", "%%"))
    command.upgrade(alembic_config, "head")

    engine = create_db_engine(test_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Session wrapped in an outer transaction that is rolled back after each test.

    Even if the test calls commit(), it only releases a SAVEPOINT, so nothing
    is left behind in the test database.
    """
    with db_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


ProviderSetter = Callable[[AIProvider], None]


@pytest.fixture
def use_provider() -> Iterator[ProviderSetter]:
    """Return a function that makes the API use the given AI provider."""

    def set_provider(provider: AIProvider) -> None:
        app.dependency_overrides[get_harness] = lambda: ChatHarness(
            provider, max_output_tokens=800
        )

    yield set_provider
    app.dependency_overrides.pop(get_harness, None)


@pytest.fixture
def client(db_session: Session, use_provider: ProviderSetter) -> Iterator[TestClient]:
    """API client wired to the test DB session and, by default, the fake provider."""
    app.dependency_overrides[get_session] = lambda: db_session
    use_provider(FakeProvider())
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_session, None)
