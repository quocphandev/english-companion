"""ai_runs records and the DAILY_AI_LIMIT check (fake or scripted providers only)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.dependencies import get_daily_ai_limit
from app.harness.prompts import PROMPT_VERSION
from app.main import app
from app.models import AiRun, Message
from app.providers.fake_provider import FakeProvider
from app.repositories.ai_run_repository import AiRunRepository
from tests.fakes import FailingProvider, ScriptedProvider
from tests.integration.conftest import ProviderSetter

VALID_JSON = '{"reply_en": "Nice!", "corrections": [], "suggested_words": []}'
TIMEZONE = "Asia/Ho_Chi_Minh"


@pytest.fixture
def set_daily_limit() -> Iterator[Any]:
    def set_limit(limit: int) -> None:
        app.dependency_overrides[get_daily_ai_limit] = lambda: limit

    yield set_limit
    app.dependency_overrides.pop(get_daily_ai_limit, None)


def create_conversation(client: TestClient) -> int:
    return client.post("/api/conversations", json={"topic": "work"}).json()[
        "conversation_id"
    ]


def send(
    client: TestClient,
    conversation_id: int,
    request_id: str,
    text_: str = "Hello there.",
) -> Any:
    return client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"request_id": request_id, "text": text_},
    )


def add_run(
    db_session: Session,
    provider: str = "gemini",
    call_count: int = 1,
    created_at: Any = None,
) -> None:
    run = AiRun(
        operation="chat_turn",
        provider=provider,
        model="m",
        prompt_version=PROMPT_VERSION,
        status="succeeded",
        call_count=call_count,
        duration_ms=1,
    )
    if created_at is not None:
        run.created_at = created_at
    db_session.add(run)
    db_session.flush()


def count_messages(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Message))


# --- Recording runs ------------------------------------------------------------


def test_successful_turn_records_a_run(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([VALID_JSON]))
    conversation_id = create_conversation(client)

    send(client, conversation_id, "req-1")

    run = db_session.scalar(select(AiRun))
    assert run is not None
    assert (run.operation, run.status, run.call_count) == ("chat_turn", "succeeded", 1)
    assert run.request_id == "req-1"
    assert run.prompt_version == PROMPT_VERSION
    assert run.error_code is None


def test_json_repair_counts_as_two_calls(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider(["broken", VALID_JSON]))
    conversation_id = create_conversation(client)

    send(client, conversation_id, "req-1")

    run = db_session.scalar(select(AiRun))
    assert run is not None
    assert run.call_count == 2


def test_failed_turn_records_its_error_code(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(FailingProvider("ai_timeout"))
    conversation_id = create_conversation(client)

    send(client, conversation_id, "req-1")

    run = db_session.scalar(select(AiRun))
    assert run is not None
    assert (run.status, run.error_code, run.call_count) == ("failed", "ai_timeout", 1)


# --- Counting today's calls --------------------------------------------------------


def test_count_ignores_fake_provider_and_other_days(db_session: Session) -> None:
    add_run(db_session, call_count=2)
    add_run(db_session, provider="fake", call_count=5)
    add_run(db_session, created_at=text("now() - interval '2 days'"))

    assert AiRunRepository(db_session).count_calls_today(TIMEZONE) == 2


def test_count_uses_the_local_calendar_day(db_session: Session) -> None:
    # Midnight today in Vietnam, expressed as a timestamptz.
    local_midnight = f"(date_trunc('day', now() AT TIME ZONE '{TIMEZONE}') AT TIME ZONE '{TIMEZONE}')"
    add_run(
        db_session, created_at=text(f"{local_midnight} - interval '1 minute'")
    )  # yesterday 23:59
    add_run(
        db_session, created_at=text(f"{local_midnight} + interval '1 second'")
    )  # today 00:00:01

    assert AiRunRepository(db_session).count_calls_today(TIMEZONE) == 1


# --- Enforcing DAILY_AI_LIMIT -------------------------------------------------------


def test_limit_reached_is_refused_before_saving_or_calling_ai(
    client: TestClient,
    db_session: Session,
    use_provider: ProviderSetter,
    set_daily_limit: Any,
) -> None:
    provider = ScriptedProvider([VALID_JSON])
    use_provider(provider)
    set_daily_limit(1)
    conversation_id = create_conversation(client)
    add_run(db_session, call_count=1)

    response = send(client, conversation_id, "req-1")

    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "daily_limit_reached"
    assert body["retryable"] is False
    assert "1 lượt" in body["message_vi"]
    assert count_messages(db_session) == 0
    assert provider.requests == []


def test_retrying_a_failed_turn_is_also_limited(
    client: TestClient,
    db_session: Session,
    use_provider: ProviderSetter,
    set_daily_limit: Any,
) -> None:
    use_provider(FailingProvider("ai_timeout"))
    set_daily_limit(1)
    conversation_id = create_conversation(client)
    send(client, conversation_id, "req-1")  # uses the only call of the day

    retry = send(client, conversation_id, "req-1")

    assert retry.status_code == 429
    assert retry.json()["code"] == "daily_limit_reached"


def test_resending_a_succeeded_turn_is_not_blocked(
    client: TestClient, use_provider: ProviderSetter, set_daily_limit: Any
) -> None:
    use_provider(ScriptedProvider([VALID_JSON]))
    set_daily_limit(1)
    conversation_id = create_conversation(client)
    first = send(client, conversation_id, "req-1")

    again = send(client, conversation_id, "req-1")

    assert again.status_code == 200
    assert again.json() == first.json()


def test_fake_provider_is_never_limited(
    client: TestClient, use_provider: ProviderSetter, set_daily_limit: Any
) -> None:
    use_provider(FakeProvider())
    set_daily_limit(0)
    conversation_id = create_conversation(client)

    response = send(client, conversation_id, "req-1")

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
