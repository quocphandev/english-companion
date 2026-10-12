"""FR05 / AC05: contextual lookup through the API, with scripted AI answers."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import get_daily_ai_limit
from app.harness.prompts import LOOKUP_PROMPT_VERSION
from app.main import app
from app.models import AiRun, LookupCache, Message
from tests.fakes import FailingProvider, ScriptedProvider
from tests.integration.conftest import ProviderSetter


def lookup_json(lemma: str, pos: str, meaning: str) -> str:
    return json.dumps(
        {
            "lemma": lemma,
            "pos": pos,
            "meaning_vi": meaning,
            "example_en": f"Example with {lemma}.",
            "sentence_meaning_vi": "Bản dịch câu.",
        }
    )


BOOK_NOUN = lookup_json("book", "noun", "quyển sách")
BOOK_VERB = lookup_json("book", "verb", "đặt (phòng)")
LOOK_AFTER = lookup_json("look after", "phrasal verb", "chăm sóc")


def chatbot_message(client: TestClient, db_session: Session, text: str) -> int:
    """Create a conversation and add a chatbot message with the given text."""
    conversation_id = client.post("/api/conversations", json={"topic": "work"}).json()[
        "conversation_id"
    ]
    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        original_text=text,
        status="succeeded",
    )
    db_session.add(message)
    db_session.flush()
    return message.id


def lookup(client: TestClient, message_id: int, text: str, selected: str) -> Any:
    start = text.index(selected)
    return client.post(
        "/api/lookup",
        json={"message_id": message_id, "start": start, "end": start + len(selected)},
    )


def count(db_session: Session, model: type) -> int:
    return db_session.scalar(select(func.count()).select_from(model))


# --- AC05: meaning depends on the sentence; phrases can be looked up ------------


def test_ac05_book_as_noun_and_verb_are_separate_lookups(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([BOOK_NOUN, BOOK_VERB])
    use_provider(provider)
    noun_text = "I read a book."
    verb_text = "I want to book a room."
    noun_id = chatbot_message(client, db_session, noun_text)
    verb_id = chatbot_message(client, db_session, verb_text)

    noun = lookup(client, noun_id, noun_text, "book").json()
    verb = lookup(client, verb_id, verb_text, "book").json()

    assert (noun["pos"], noun["meaning_vi"]) == ("noun", "quyển sách")
    assert (verb["pos"], verb["meaning_vi"]) == ("verb", "đặt (phòng)")
    # Each request carried its own sentence, with the selection marked.
    assert "I read a ⟦book⟧." in provider.requests[0].messages[-1].content
    assert "I want to ⟦book⟧ a room." in provider.requests[1].messages[-1].content
    assert count(db_session, LookupCache) == 2


def test_ac05_phrase_looks_after_is_looked_up_as_a_whole(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([LOOK_AFTER])
    use_provider(provider)
    text = "She looks after her sister."
    message_id = chatbot_message(client, db_session, text)

    body = lookup(client, message_id, text, "looks after").json()

    assert body["selected_text"] == "looks after"
    assert (body["lemma"], body["meaning_vi"]) == ("look after", "chăm sóc")
    assert "⟦looks after⟧" in provider.requests[0].messages[-1].content


# --- Cache ------------------------------------------------------------------------


def test_second_identical_lookup_comes_from_cache_without_ai(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([BOOK_NOUN])
    use_provider(provider)
    text = "I read a book."
    message_id = chatbot_message(client, db_session, text)

    first = lookup(client, message_id, text, "book").json()
    second = lookup(client, message_id, text, "book").json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["meaning_vi"] == first["meaning_vi"]
    assert len(provider.requests) == 1
    runs = db_session.scalars(select(AiRun)).all()
    assert [(r.operation, r.prompt_version) for r in runs] == [
        ("lookup", LOOKUP_PROMPT_VERSION)
    ]


def test_response_returns_sentence_and_offsets_for_saving_later(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([BOOK_VERB]))
    text = "Hello! I want to book a room."
    message_id = chatbot_message(client, db_session, text)

    body = lookup(client, message_id, text, "book").json()

    assert body["source_sentence"] == "I want to book a room."
    sentence = body["source_sentence"]
    assert sentence[body["sentence_start"] : body["sentence_end"]] == "book"


# --- Errors -----------------------------------------------------------------------


def test_nine_words_are_refused(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([])
    use_provider(provider)
    text = "one two three four five six seven eight nine."
    message_id = chatbot_message(client, db_session, text)

    response = lookup(
        client, message_id, text, "one two three four five six seven eight nine"
    )

    assert response.status_code == 422
    assert response.json()["code"] == "selection_too_long"
    assert provider.requests == []


@pytest.mark.parametrize(
    ("start", "end", "code"),
    [
        pytest.param(5, 2, "invalid_input", id="end before start"),
        pytest.param(0, 999, "invalid_selection", id="past the end"),
    ],
)
def test_bad_offsets_are_refused(
    client: TestClient, db_session: Session, start: int, end: int, code: str
) -> None:
    message_id = chatbot_message(client, db_session, "I read a book.")

    response = client.post(
        "/api/lookup", json={"message_id": message_id, "start": start, "end": end}
    )

    assert response.status_code == 422
    assert response.json()["code"] == code


def test_unknown_message_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/lookup", json={"message_id": 999_999, "start": 0, "end": 1}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "message_not_found"


def test_provider_error_returns_structured_failure_and_caches_nothing(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(FailingProvider("ai_rate_limited"))
    text = "I read a book."
    message_id = chatbot_message(client, db_session, text)

    body = lookup(client, message_id, text, "book").json()

    assert body["status"] == "failed"
    assert body["error"]["code"] == "ai_rate_limited"
    assert body["selected_text"] == "book"
    assert count(db_session, LookupCache) == 0


def test_daily_limit_blocks_uncached_lookups(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    provider = ScriptedProvider([BOOK_NOUN])
    use_provider(provider)
    text = "I read a book."
    message_id = chatbot_message(client, db_session, text)
    app.dependency_overrides[get_daily_ai_limit] = lambda: 0
    try:
        response = lookup(client, message_id, text, "book")
    finally:
        app.dependency_overrides.pop(get_daily_ai_limit, None)

    assert response.status_code == 429
    assert provider.requests == []
