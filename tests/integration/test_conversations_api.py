from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.harness.prompts import PROMPT_VERSION
from app.models import Correction, Message, Profile
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import MAX_MESSAGE_CHARS
from tests.fakes import RecordingFakeProvider, ScriptedProvider
from tests.integration.conftest import ProviderSetter

BROKEN_JSON = "not json at all"


def create_conversation(client: TestClient, **overrides: Any) -> int:
    body = {"topic": "work", **overrides}
    response = client.post("/api/conversations", json=body)
    assert response.status_code == 201
    return response.json()["conversation_id"]


def send(client: TestClient, conversation_id: int, request_id: str, text: str) -> Any:
    return client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"request_id": request_id, "text": text},
    )


def count_messages(db_session: Session, role: str) -> int:
    return db_session.scalar(
        select(func.count()).select_from(Message).where(Message.role == role)
    )


# --- POST /api/conversations -------------------------------------------------


def test_create_conversation_updates_the_single_profile(
    client: TestClient, db_session: Session
) -> None:
    create_conversation(client)
    create_conversation(client, level="B1", correction_mode="conversation")

    profiles = db_session.scalars(select(Profile)).all()
    assert len(profiles) == 1
    assert profiles[0].level == "B1"
    assert profiles[0].correction_mode == "conversation"


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"topic": "   "}, id="blank topic"),
        pytest.param({"topic": "work", "level": "C2"}, id="unknown level"),
    ],
)
def test_create_conversation_rejects_invalid_input(
    client: TestClient, body: dict[str, Any]
) -> None:
    response = client.post("/api/conversations", json=body)

    assert response.status_code == 422
    assert response.json() == {
        "code": "invalid_input",
        "message_vi": "Dữ liệu gửi lên không hợp lệ.",
        "retryable": False,
    }


# --- POST /api/conversations/{id}/messages: happy path -----------------------


def test_send_message_saves_turn_with_reply_and_corrections(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = create_conversation(client)

    response = send(client, conversation_id, "req-1", "Yesterday I go to work.")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["error"] is None
    assert body["message"]["role"] == "user"
    assert body["message"]["text"] == "Yesterday I go to work."
    assert body["message"]["status"] == "succeeded"
    assert body["reply"]["role"] == "assistant"
    assert body["reply"]["text"] == "That sounds nice! What did you do after that?"
    assert body["corrections"][0]["corrected_text"] == "I went"

    user_message = db_session.get(Message, body["message"]["id"])
    assert user_message is not None
    assert user_message.status == "succeeded"
    correction = db_session.scalar(select(Correction))
    assert correction is not None
    assert correction.message_id == user_message.id
    assert correction.prompt_version == PROMPT_VERSION


def test_original_text_is_stored_unchanged(client: TestClient) -> None:
    conversation_id = create_conversation(client)

    body = send(client, conversation_id, "req-1", "  Xin chào, I am Quoc.  ").json()

    assert body["message"]["text"] == "  Xin chào, I am Quoc.  "


def test_context_uses_only_this_conversation_history(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    provider = RecordingFakeProvider()
    use_provider(provider)
    first_id = create_conversation(client)
    send(client, first_id, "req-1", "I like coffee.")
    send(client, first_id, "req-2", "I drink it every day.")
    second_id = create_conversation(client, topic="coffee shop")
    send(client, second_id, "req-3", "Hello!")

    second_turn = [m.content for m in provider.requests[1].messages]
    new_conversation = [m.content for m in provider.requests[2].messages]
    assert second_turn == [
        "I like coffee.",
        "That sounds nice! What did you do after that?",
        "I drink it every day.",
    ]
    assert new_conversation == ["Hello!"]


# --- AC01: input limits -------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected_code"),
    [
        pytest.param("", "empty_message", id="empty"),
        pytest.param("   \n\t ", "empty_message", id="whitespace only"),
        pytest.param(
            "a" * (MAX_MESSAGE_CHARS + 1), "message_too_long", id="2001 chars"
        ),
    ],
)
def test_send_message_rejects_empty_or_too_long_text(
    client: TestClient, db_session: Session, text: str, expected_code: str
) -> None:
    conversation_id = create_conversation(client)

    response = send(client, conversation_id, "req-1", text)

    assert response.status_code == 422
    assert response.json()["code"] == expected_code
    assert response.json()["retryable"] is False
    assert count_messages(db_session, "user") == 0


def test_send_message_accepts_exactly_max_length(client: TestClient) -> None:
    conversation_id = create_conversation(client)

    response = send(client, conversation_id, "req-1", "a" * MAX_MESSAGE_CHARS)

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_send_message_rejects_invalid_request_id(client: TestClient) -> None:
    conversation_id = create_conversation(client)

    response = send(client, conversation_id, "bad id with spaces", "Hello")

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_input"


# --- AC01: idempotency ----------------------------------------------------------


def test_same_request_id_twice_creates_one_turn(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = RecordingFakeProvider()
    use_provider(provider)
    conversation_id = create_conversation(client)

    first = send(client, conversation_id, "req-1", "Yesterday I go to work.")
    second = send(client, conversation_id, "req-1", "Yesterday I go to work.")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(provider.requests) == 1
    assert count_messages(db_session, "user") == 1
    assert count_messages(db_session, "assistant") == 1


def test_concurrent_duplicate_is_caught_by_unique_constraint(
    client: TestClient,
    db_session: Session,
    use_provider: ProviderSetter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = RecordingFakeProvider()
    use_provider(provider)
    conversation_id = create_conversation(client)
    first = send(client, conversation_id, "req-1", "Hello there.")

    # Simulate a second request that checked before the first one was saved:
    # the lookup misses once, so the INSERT hits the UNIQUE constraint.
    real_find = ConversationRepository.find_message_by_request_id
    calls = {"count": 0}

    def find_missing_once(self: ConversationRepository, request_id: str) -> Any:
        calls["count"] += 1
        return None if calls["count"] == 1 else real_find(self, request_id)

    monkeypatch.setattr(
        ConversationRepository, "find_message_by_request_id", find_missing_once
    )
    second = send(client, conversation_id, "req-1", "Hello there.")

    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(provider.requests) == 1
    assert count_messages(db_session, "user") == 1


def test_reused_request_id_with_different_text_is_rejected(
    client: TestClient,
) -> None:
    conversation_id = create_conversation(client)
    send(client, conversation_id, "req-1", "First message.")

    response = send(client, conversation_id, "req-1", "A different message.")

    assert response.status_code == 409
    assert response.json()["code"] == "request_id_conflict"


def test_unknown_conversation_returns_404(client: TestClient) -> None:
    response = send(client, 999_999, "req-1", "Hello")

    assert response.status_code == 404
    assert response.json() == {
        "code": "conversation_not_found",
        "message_vi": "Không tìm thấy cuộc trò chuyện.",
        "retryable": False,
    }


# --- AI failure keeps the user's text and can be retried ----------------------


def test_invalid_ai_output_marks_turn_failed_and_keeps_text(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([BROKEN_JSON, BROKEN_JSON]))
    conversation_id = create_conversation(client)

    response = send(client, conversation_id, "req-1", "Yesterday I go to work.")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["reply"] is None
    assert body["corrections"] == []
    assert body["error"]["code"] == "invalid_ai_output"
    assert body["error"]["retryable"] is True
    assert BROKEN_JSON not in response.text
    user_message = db_session.get(Message, body["message"]["id"])
    assert user_message is not None
    assert user_message.status == "failed"
    assert user_message.original_text == "Yesterday I go to work."
    assert count_messages(db_session, "assistant") == 0


def test_retry_after_failure_reuses_the_same_message(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([BROKEN_JSON, BROKEN_JSON]))
    conversation_id = create_conversation(client)
    failed = send(client, conversation_id, "req-1", "Yesterday I go to work.").json()

    use_provider(RecordingFakeProvider())
    retried = send(client, conversation_id, "req-1", "Yesterday I go to work.").json()

    assert retried["status"] == "succeeded"
    assert retried["message"]["id"] == failed["message"]["id"]
    assert retried["reply"] is not None
    assert count_messages(db_session, "user") == 1
