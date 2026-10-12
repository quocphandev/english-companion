"""The demo seed script adds a usable conversation and words, once, without AI."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Conversation, Correction, Message, Vocabulary, VocabularySource
from scripts.seed_demo import DEMO_TOPIC, seed_demo


def count(db_session: Session, model: type) -> int:
    return db_session.scalar(select(func.count()).select_from(model))


def test_seed_creates_demo_data_once(db_session: Session) -> None:
    conversation_id = seed_demo(db_session)
    second = seed_demo(db_session)

    assert conversation_id is not None
    assert second is None
    assert count(db_session, Conversation) == 1
    assert count(db_session, Message) == 5
    assert count(db_session, Correction) == 1
    assert count(db_session, Vocabulary) == 2
    sources = db_session.scalars(select(VocabularySource)).all()
    for source in sources:
        selected = source.source_sentence[source.selected_start : source.selected_end]
        assert selected in {"book", "looks after"}


def test_seeded_data_shows_in_the_pages(
    client: TestClient, db_session: Session
) -> None:
    conversation_id = seed_demo(db_session)

    chat = client.get(f"/conversations/{conversation_id}").text
    words = client.get("/api/vocabulary").json()

    assert DEMO_TOPIC in chat
    assert "I went" in chat
    assert {word["lemma"] for word in words} == {"book", "look after"}
