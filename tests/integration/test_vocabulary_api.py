"""FR06 / AC06: saving looked-up words without duplicates, and managing them."""

import json
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Message, Vocabulary, VocabularySource
from tests.fakes import ScriptedProvider
from tests.integration.conftest import ProviderSetter


def lookup_json(pos: str, meaning: str) -> str:
    return json.dumps(
        {
            "lemma": "Book",
            "pos": pos,
            "meaning_vi": meaning,
            "example_en": "An example.",
        }
    )


def chatbot_message(client: TestClient, db_session: Session, text: str) -> int:
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


def offsets(text: str, selected: str) -> dict[str, int]:
    start = text.index(selected)
    return {"start": start, "end": start + len(selected)}


def look_up(client: TestClient, message_id: int, text: str, selected: str) -> Any:
    body = {"message_id": message_id, **offsets(text, selected)}
    return client.post("/api/lookup", json=body).json()


def save(
    client: TestClient, message_id: int, text: str, selected: str, meaning: str
) -> Any:
    body = {"message_id": message_id, **offsets(text, selected), "meaning_vi": meaning}
    return client.post("/api/vocabulary", json=body)


def count(db_session: Session, model: type) -> int:
    return db_session.scalar(select(func.count()).select_from(model))


# --- AC06 -------------------------------------------------------------------------


def test_ac06_same_word_same_meaning_is_not_duplicated(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([lookup_json("noun", "quyển sách")] * 2))
    first_text = "I read a book."
    second_text = "This book is long."
    first_id = chatbot_message(client, db_session, first_text)
    second_id = chatbot_message(client, db_session, second_text)
    look_up(client, first_id, first_text, "book")
    look_up(client, second_id, second_text, "book")

    created = save(client, first_id, first_text, "book", "quyển sách")
    again = save(client, first_id, first_text, "book", "Quyển  sách!")
    other_sentence = save(client, second_id, second_text, "book", "quyển sách")

    assert created.status_code == 201
    assert created.json()["created"] is True
    assert again.status_code == 200
    assert again.json()["created"] is False
    assert other_sentence.json()["created"] is False
    assert count(db_session, Vocabulary) == 1
    # Same place saved twice adds nothing; a new sentence adds a source.
    sources = other_sentence.json()["word"]["sources"]
    assert [s["source_sentence"] for s in sources] == [first_text, second_text]


def test_ac06_same_word_with_another_meaning_is_a_separate_entry(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(
        ScriptedProvider(
            [lookup_json("noun", "quyển sách"), lookup_json("verb", "đặt (phòng)")]
        )
    )
    noun_text = "I read a book."
    verb_text = "I want to book a room."
    noun_id = chatbot_message(client, db_session, noun_text)
    verb_id = chatbot_message(client, db_session, verb_text)
    look_up(client, noun_id, noun_text, "book")
    look_up(client, verb_id, verb_text, "book")

    noun = save(client, noun_id, noun_text, "book", "quyển sách").json()
    verb = save(client, verb_id, verb_text, "book", "đặt (phòng)").json()

    assert noun["created"] is True
    assert verb["created"] is True
    assert noun["word"]["id"] != verb["word"]["id"]
    assert (noun["word"]["lemma"], noun["word"]["pos"]) == ("book", "noun")
    assert verb["word"]["pos"] == "verb"
    assert count(db_session, Vocabulary) == 2


def test_learner_can_edit_the_meaning_before_saving(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([lookup_json("noun", "quyển sách")]))
    text = "I read a book."
    message_id = chatbot_message(client, db_session, text)
    look_up(client, message_id, text, "book")

    word = save(client, message_id, text, "book", "cuốn sách (tài liệu đọc)").json()[
        "word"
    ]

    assert word["meaning_vi"] == "cuốn sách (tài liệu đọc)"
    assert word["example_en"] == "An example."


def test_saving_without_a_lookup_is_refused(
    client: TestClient, db_session: Session
) -> None:
    text = "I read a book."
    message_id = chatbot_message(client, db_session, text)

    response = save(client, message_id, text, "book", "quyển sách")

    assert response.status_code == 409
    assert response.json()["code"] == "lookup_required"
    assert count(db_session, Vocabulary) == 0


def test_deleting_the_message_keeps_the_word_but_drops_the_link(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([lookup_json("noun", "quyển sách")]))
    text = "I read a book."
    message_id = chatbot_message(client, db_session, text)
    look_up(client, message_id, text, "book")
    save(client, message_id, text, "book", "quyển sách")

    db_session.delete(db_session.get(Message, message_id))
    db_session.flush()

    assert count(db_session, Vocabulary) == 1
    assert count(db_session, VocabularySource) == 0


# --- Managing the list ------------------------------------------------------------


def saved_word(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> int:
    use_provider(ScriptedProvider([lookup_json("noun", "quyển sách")]))
    text = "I read a book."
    message_id = chatbot_message(client, db_session, text)
    look_up(client, message_id, text, "book")
    return save(client, message_id, text, "book", "quyển sách").json()["word"]["id"]


def test_list_and_search_words(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    saved_word(client, db_session, use_provider)

    assert [w["lemma"] for w in client.get("/api/vocabulary").json()] == ["book"]
    assert len(client.get("/api/vocabulary", params={"q": "sách"}).json()) == 1
    assert client.get("/api/vocabulary", params={"q": "coffee"}).json() == []
    # LIKE wildcards in the query are treated as plain text.
    assert client.get("/api/vocabulary", params={"q": "%"}).json() == []


def test_edit_note_and_delete(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    word_id = saved_word(client, db_session, use_provider)

    edited = client.patch(
        f"/api/vocabulary/{word_id}", json={"note": "Hay gặp ở thư viện"}
    )
    deleted = client.delete(f"/api/vocabulary/{word_id}")
    missing = client.delete(f"/api/vocabulary/{word_id}")

    assert edited.json()["note"] == "Hay gặp ở thư viện"
    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert missing.json()["code"] == "word_not_found"


def test_changing_meaning_to_an_existing_one_is_refused(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(
        ScriptedProvider(
            [lookup_json("noun", "quyển sách"), lookup_json("verb", "đặt")]
        )
    )
    noun_text = "I read a book."
    verb_text = "I want to book a room."
    noun_id = chatbot_message(client, db_session, noun_text)
    verb_id = chatbot_message(client, db_session, verb_text)
    look_up(client, noun_id, noun_text, "book")
    look_up(client, verb_id, verb_text, "book")
    save(client, noun_id, noun_text, "book", "quyển sách")
    verb_word = save(client, verb_id, verb_text, "book", "đặt").json()["word"]

    response = client.patch(
        f"/api/vocabulary/{verb_word['id']}", json={"meaning_vi": "Quyển sách"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_meaning"
