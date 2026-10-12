"""FR10 / AC04 (summary part): finishing a session and its summary."""

import json
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_daily_ai_limit
from app.harness.prompts import SUMMARY_PROMPT_VERSION
from app.main import app
from app.models import AiRun, Conversation
from tests.fakes import FailingProvider, ScriptedProvider
from tests.integration.conftest import ProviderSetter

TURN_WITH_ERROR = json.dumps(
    {
        "reply_en": "Nice! Where do you work?",
        "corrections": [
            {
                "category": "grammar",
                "original_span": "I go",
                "corrected_text": "I went",
                "explanation_vi": "Quá khứ đơn.",
            }
        ],
    }
)
SUMMARY = json.dumps(
    {
        "recap_vi": "Bạn kể về công việc hôm qua.",
        "key_words": [
            {"text": "work", "meaning_vi": "công việc"},
            {"text": "airport", "meaning_vi": "sân bay"},
        ],
        "next_exercise_vi": "Kể 3 việc đã làm hôm qua.",
    }
)


def start(client: TestClient, mode: str = "learning") -> int:
    body = {"topic": "work", "correction_mode": mode}
    return client.post("/api/conversations", json=body).json()["conversation_id"]


def send(client: TestClient, conversation_id: int, request_id: str, text: str) -> Any:
    return client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"request_id": request_id, "text": text},
    )


def finish(client: TestClient, conversation_id: int) -> Any:
    return client.post(f"/api/conversations/{conversation_id}/finish")


def test_finish_returns_recap_errors_words_and_next_exercise(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([TURN_WITH_ERROR, SUMMARY]))
    conversation_id = start(client)
    send(client, conversation_id, "req-1", "Yesterday I go to work.")

    response = finish(client, conversation_id)

    assert response.status_code == 200
    body = response.json()
    assert body["recap_vi"] == "Bạn kể về công việc hôm qua."
    assert body["next_exercise_vi"] == "Kể 3 việc đã làm hôm qua."
    assert [(e["original_span"], e["corrected_text"]) for e in body["errors"]] == [
        ("I go", "I went")
    ]
    # "airport" was never said in the conversation, so it is dropped.
    assert [w["text"] for w in body["words"]] == ["work"]
    assert body["ai_error"] is None
    conversation = db_session.get(Conversation, conversation_id)
    assert conversation is not None
    assert conversation.status == "finished"
    assert conversation.finished_at is not None
    runs = db_session.scalars(select(AiRun).where(AiRun.operation == "summary")).all()
    assert [r.prompt_version for r in runs] == [SUMMARY_PROMPT_VERSION]


def test_ac04_conversation_mode_errors_are_in_the_summary(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([TURN_WITH_ERROR, SUMMARY]))
    conversation_id = start(client, mode="conversation")
    send(client, conversation_id, "req-1", "Yesterday I go to work.")

    body = finish(client, conversation_id).json()

    assert body["errors"][0]["corrected_text"] == "I went"


def test_ai_failure_still_finishes_with_errors_listed(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([TURN_WITH_ERROR])
    use_provider(provider)
    conversation_id = start(client)
    send(client, conversation_id, "req-1", "Yesterday I go to work.")
    use_provider(FailingProvider("ai_unavailable"))

    body = finish(client, conversation_id).json()

    assert body["recap_vi"] is None
    assert body["ai_error"]["code"] == "ai_unavailable"
    assert body["errors"][0]["original_span"] == "I go"
    conversation = db_session.get(Conversation, conversation_id)
    assert conversation is not None
    assert conversation.status == "finished"


def test_daily_limit_still_finishes_without_ai(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([TURN_WITH_ERROR])
    use_provider(provider)
    conversation_id = start(client)
    send(client, conversation_id, "req-1", "Yesterday I go to work.")
    app.dependency_overrides[get_daily_ai_limit] = lambda: 0
    try:
        body = finish(client, conversation_id).json()
    finally:
        app.dependency_overrides.pop(get_daily_ai_limit, None)

    assert body["ai_error"]["code"] == "daily_limit_reached"
    assert len(provider.requests) == 1  # only the chat turn
    assert body["errors"]


def test_empty_session_finishes_without_calling_the_ai(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([])
    use_provider(provider)
    conversation_id = start(client)

    body = finish(client, conversation_id).json()

    assert provider.requests == []
    assert body["recap_vi"] is None
    assert body["ai_error"] is None


def test_finishing_twice_does_not_call_the_ai_again(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([TURN_WITH_ERROR, SUMMARY])
    use_provider(provider)
    conversation_id = start(client)
    send(client, conversation_id, "req-1", "Yesterday I go to work.")

    first = finish(client, conversation_id).json()
    second = finish(client, conversation_id).json()

    assert second == first
    assert len(provider.requests) == 2


def test_finished_session_takes_no_new_messages_or_help(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([TURN_WITH_ERROR, SUMMARY]))
    conversation_id = start(client)
    first = send(client, conversation_id, "req-1", "Yesterday I go to work.").json()
    finish(client, conversation_id)

    new_turn = send(client, conversation_id, "req-2", "One more thing.")
    resent = send(client, conversation_id, "req-1", "Yesterday I go to work.")
    help_response = client.post("/api/help", json={"conversation_id": conversation_id})

    assert new_turn.status_code == 409
    assert new_turn.json()["code"] == "conversation_finished"
    assert resent.status_code == 200  # a done turn can still be read back
    assert resent.json() == first
    assert help_response.status_code == 409


def test_finished_page_shows_the_summary_instead_of_the_input(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([TURN_WITH_ERROR, SUMMARY]))
    conversation_id = start(client)
    send(client, conversation_id, "req-1", "Yesterday I go to work.")
    finish(client, conversation_id)

    html = client.get(f"/conversations/{conversation_id}").text

    assert "Tổng kết buổi học" in html
    assert "Bạn kể về công việc hôm qua." in html
    assert 'id="message-form"' not in html
    assert 'id="finish-button"' not in html


def test_unknown_conversation_cannot_be_finished(client: TestClient) -> None:
    response = finish(client, 999_999)

    assert response.status_code == 404
