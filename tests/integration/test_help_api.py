"""FR03 / AC07: help is suggested, stored for review, and never sent as a message."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import get_daily_ai_limit
from app.harness.prompts import HELP_PROMPT_VERSION
from app.main import app
from app.models import AiRun, HelpRequest, Message
from tests.fakes import FailingProvider, ScriptedProvider
from tests.integration.conftest import ProviderSetter

HINT = "I usually take the bus to work."
HELP_JSON = json.dumps(
    {
        "hint_en": HINT,
        "words": [{"text": "take the bus", "meaning_vi": "đi xe buýt"}],
        "explanation_vi": "Dùng 'take the bus' để nói về phương tiện.",
    }
)


def create_conversation(client: TestClient) -> int:
    response = client.post("/api/conversations", json={"topic": "work"})
    return response.json()["conversation_id"]


def ask_help(client: TestClient, conversation_id: int, **body: Any) -> Any:
    return client.post("/api/help", json={"conversation_id": conversation_id, **body})


def count(db_session: Session, model: type) -> int:
    return db_session.scalar(select(func.count()).select_from(model))


@pytest.mark.parametrize(
    ("level", "mode"), [(1, "words"), (2, "starter"), (3, "sample")]
)
def test_each_level_returns_a_suggestion(
    client: TestClient, use_provider: ProviderSetter, level: int, mode: str
) -> None:
    use_provider(ScriptedProvider([HELP_JSON]))
    conversation_id = create_conversation(client)

    response = ask_help(client, conversation_id, level=level)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["mode"] == mode
    assert body["hint_en"] == HINT
    assert body["words"][0]["meaning_vi"] == "đi xe buýt"
    assert body["explanation_vi"]


def test_vietnamese_idea_is_answered_in_intent_mode(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([HELP_JSON])
    use_provider(provider)
    conversation_id = create_conversation(client)

    body = ask_help(client, conversation_id, level=3, intent_vi="Tôi bị kẹt xe").json()

    assert body["mode"] == "intent"
    assert "Tôi bị kẹt xe" in provider.requests[0].messages[-1].content
    stored = db_session.scalar(select(HelpRequest))
    assert stored is not None
    assert (stored.mode, stored.intent_vi) == ("intent", "Tôi bị kẹt xe")


def test_ac07_help_never_creates_a_message(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([HELP_JSON]))
    conversation_id = create_conversation(client)

    ask_help(client, conversation_id, level=3)

    learner_messages = db_session.scalar(
        select(func.count()).select_from(Message).where(Message.role == "user")
    )
    assert learner_messages == 0


def test_help_use_is_recorded_for_review_and_counted(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([HELP_JSON]))
    conversation_id = create_conversation(client)

    ask_help(client, conversation_id, level=2)

    stored = db_session.scalar(select(HelpRequest))
    assert stored is not None
    assert (stored.mode, stored.status, stored.hint_en) == (
        "starter",
        "succeeded",
        HINT,
    )
    run = db_session.scalar(select(AiRun))
    assert run is not None
    assert (run.operation, run.prompt_version) == ("help", HELP_PROMPT_VERSION)


def test_provider_error_returns_structured_failure(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(FailingProvider("ai_timeout"))
    conversation_id = create_conversation(client)

    body = ask_help(client, conversation_id, level=1).json()

    assert body["status"] == "failed"
    assert body["hint_en"] is None
    assert body["error"]["code"] == "ai_timeout"
    assert body["error"]["retryable"] is True
    stored = db_session.scalar(select(HelpRequest))
    assert stored is not None
    assert stored.status == "failed"


def test_daily_limit_blocks_help_before_calling_ai(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([HELP_JSON])
    use_provider(provider)
    app.dependency_overrides[get_daily_ai_limit] = lambda: 0
    try:
        conversation_id = create_conversation(client)
        response = ask_help(client, conversation_id, level=1)
    finally:
        app.dependency_overrides.pop(get_daily_ai_limit, None)

    assert response.status_code == 429
    assert response.json()["code"] == "daily_limit_reached"
    assert provider.requests == []
    assert count(db_session, HelpRequest) == 0


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"level": 4}, id="level out of range"),
        pytest.param({"level": 1, "intent_vi": "x" * 501}, id="idea too long"),
    ],
)
def test_invalid_help_request_is_rejected(
    client: TestClient, body: dict[str, Any]
) -> None:
    conversation_id = create_conversation(client)

    response = ask_help(client, conversation_id, **body)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_input"


def test_unknown_conversation_returns_404(client: TestClient) -> None:
    response = ask_help(client, 999_999, level=1)

    assert response.status_code == 404
    assert response.json()["code"] == "conversation_not_found"
