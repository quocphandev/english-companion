"""Mốc 4: deleting a conversation or all learning data, and flagging chatbot replies."""

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import get_allow_delete
from app.main import app
from app.models import (
    AiRun,
    Conversation,
    Correction,
    HelpRequest,
    LookupCache,
    Message,
    Profile,
    ReviewEvent,
    Vocabulary,
    VocabularySource,
)
from app.services.data_service import DELETE_ALL_CONFIRMATION
from tests.fakes import ScriptedProvider
from tests.integration.conftest import ProviderSetter

TURN = json.dumps(
    {
        "reply_en": "I read a book about it.",
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
LOOKUP = json.dumps(
    {
        "lemma": "book",
        "pos": "noun",
        "meaning_vi": "quyển sách",
        "example_en": "A book.",
    }
)
HELP = json.dumps({"hint_en": "I went to ...", "explanation_vi": "Gợi ý."})


def count(db_session: Session, model: type) -> int:
    return db_session.scalar(select(func.count()).select_from(model))


def full_session(client: TestClient, use_provider: ProviderSetter) -> tuple[int, int]:
    """A conversation with a turn, a correction, help, a saved word and a review."""
    use_provider(ScriptedProvider([TURN, LOOKUP, HELP]))
    conversation_id = client.post("/api/conversations", json={"topic": "work"}).json()[
        "conversation_id"
    ]
    reply = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"request_id": "req-1", "text": "Yesterday I go to work."},
    ).json()["reply"]
    text = reply["text"]
    start = text.index("book")
    selection = {"message_id": reply["id"], "start": start, "end": start + 4}
    client.post("/api/lookup", json=selection)
    word = client.post(
        "/api/vocabulary", json={**selection, "meaning_vi": "quyển sách"}
    ).json()
    client.post(
        "/api/reviews", json={"vocabulary_id": word["word"]["id"], "outcome": "again"}
    )
    client.post("/api/help", json={"conversation_id": conversation_id, "level": 1})
    return conversation_id, reply["id"]


def test_deleting_a_conversation_keeps_saved_words(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    conversation_id, _ = full_session(client, use_provider)

    response = client.delete(f"/api/conversations/{conversation_id}")

    assert response.status_code == 204
    for model in (Conversation, Message, Correction, HelpRequest, VocabularySource):
        assert count(db_session, model) == 0, model.__name__
    assert count(db_session, Vocabulary) == 1
    assert count(db_session, ReviewEvent) == 1
    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 404


def test_delete_all_needs_the_exact_confirmation(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    full_session(client, use_provider)

    response = client.post("/api/data/delete-all", json={"confirm": "xoa"})

    assert response.status_code == 422
    assert response.json()["code"] == "confirmation_mismatch"
    assert count(db_session, Conversation) == 1


def test_delete_all_removes_learning_data_but_keeps_usage_records(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    full_session(client, use_provider)
    runs_before = count(db_session, AiRun)

    response = client.post(
        "/api/data/delete-all", json={"confirm": DELETE_ALL_CONFIRMATION.lower()}
    )

    assert response.status_code == 204
    for model in (
        Conversation,
        Message,
        Vocabulary,
        ReviewEvent,
        LookupCache,
        HelpRequest,
    ):
        assert count(db_session, model) == 0, model.__name__
    # Usage metadata stays, so deleting data cannot reset the daily limit.
    assert count(db_session, AiRun) == runs_before
    assert count(db_session, Profile) == 1


def test_chatbot_reply_can_be_flagged_and_unflagged(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    conversation_id, reply_id = full_session(client, use_provider)

    flagged = client.post(
        f"/api/messages/{reply_id}/review-flag", json={"needs_review": True}
    )
    html = client.get(f"/conversations/{conversation_id}").text
    unflagged = client.post(
        f"/api/messages/{reply_id}/review-flag", json={"needs_review": False}
    )

    assert flagged.json() == {"message_id": reply_id, "needs_review": True}
    assert "⚑ Đã đánh dấu" in html
    assert unflagged.json()["needs_review"] is False
    message = db_session.get(Message, reply_id)
    assert message is not None
    assert message.needs_review is False


def test_only_chatbot_replies_can_be_flagged(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    full_session(client, use_provider)
    user_message = db_session.scalar(select(Message).where(Message.role == "user"))
    assert user_message is not None

    response: Any = client.post(
        f"/api/messages/{user_message.id}/review-flag", json={"needs_review": True}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "reply_not_found"


def test_chat_page_shows_disclaimer_and_delete_button(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    conversation_id, _ = full_session(client, use_provider)

    html = client.get(f"/conversations/{conversation_id}").text

    assert "AI có thể sai" in html
    assert 'id="delete-conversation"' in html
    assert 'id="delete-conversation-dialog"' in html


def test_settings_page_offers_delete_all(client: TestClient) -> None:
    html = client.get("/settings").text

    assert 'aria-current="page">Cài đặt</a>' in html
    assert DELETE_ALL_CONFIRMATION in html
    assert 'id="delete-all-form"' in html


@pytest.fixture
def public_demo() -> Iterator[None]:
    app.dependency_overrides[get_allow_delete] = lambda: False
    yield
    app.dependency_overrides.pop(get_allow_delete, None)


@pytest.mark.usefixtures("public_demo")
def test_public_demo_disables_deleting(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    conversation_id, _ = full_session(client, use_provider)

    one = client.delete(f"/api/conversations/{conversation_id}")
    everything = client.post(
        "/api/data/delete-all", json={"confirm": DELETE_ALL_CONFIRMATION}
    )
    chat = client.get(f"/conversations/{conversation_id}").text
    settings = client.get("/settings").text

    assert one.status_code == 403
    assert one.json()["code"] == "deleting_disabled"
    assert everything.status_code == 403
    assert count(db_session, Conversation) == 1
    assert 'id="delete-conversation"' not in chat
    assert 'id="delete-all-form"' not in settings
    assert "bản demo dùng chung" in settings
