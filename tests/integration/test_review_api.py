"""FR07 (MVP): manual flashcards, review outcomes and the reviewed filter."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Message, Profile, ReviewEvent, Vocabulary, VocabularySource
from app.services.review_service import BLANK


def make_profile(client: TestClient, db_session: Session) -> tuple[int, int]:
    conversation_id = client.post("/api/conversations", json={"topic": "work"}).json()[
        "conversation_id"
    ]
    return db_session.scalars(select(Profile)).one().id, conversation_id


def add_word(
    db_session: Session,
    profile_id: int,
    lemma: str,
    *,
    example: str = "An example.",
    source: tuple[int, str, str] | None = None,
) -> int:
    word = Vocabulary(
        profile_id=profile_id,
        lemma=lemma,
        selected_text=lemma,
        meaning_vi=f"nghĩa của {lemma}",
        meaning_key=f"nghĩa của {lemma}",
        pos="noun",
        example_en=example,
    )
    db_session.add(word)
    db_session.flush()
    if source is not None:
        conversation_id, sentence, selected = source
        message = Message(
            conversation_id=conversation_id,
            role="assistant",
            original_text=sentence,
            status="succeeded",
        )
        db_session.add(message)
        db_session.flush()
        start = sentence.index(selected)
        db_session.add(
            VocabularySource(
                vocabulary_id=word.id,
                message_id=message.id,
                source_sentence=sentence,
                selected_start=start,
                selected_end=start + len(selected),
            )
        )
        db_session.flush()
    return word.id


def review(client: TestClient, word_id: int, outcome: str) -> object:
    return client.post(
        "/api/reviews", json={"vocabulary_id": word_id, "outcome": outcome}
    )


def test_review_outcome_is_recorded(client: TestClient, db_session: Session) -> None:
    profile_id, _ = make_profile(client, db_session)
    word_id = add_word(db_session, profile_id, "book")

    response = review(client, word_id, "remembered")

    assert response.status_code == 201
    assert response.json()["outcome"] == "remembered"
    event = db_session.scalar(select(ReviewEvent))
    assert event is not None
    assert (event.vocabulary_id, event.outcome) == (word_id, "remembered")


def test_invalid_outcome_and_unknown_word_are_refused(
    client: TestClient, db_session: Session
) -> None:
    profile_id, _ = make_profile(client, db_session)
    word_id = add_word(db_session, profile_id, "book")

    bad_outcome = review(client, word_id, "maybe")
    unknown = review(client, 999_999, "again")

    assert bad_outcome.status_code == 422
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "word_not_found"


def test_deck_order_is_new_then_again_then_remembered(
    client: TestClient, db_session: Session
) -> None:
    profile_id, _ = make_profile(client, db_session)
    remembered = add_word(db_session, profile_id, "apple")
    again = add_word(db_session, profile_id, "banana")
    new = add_word(db_session, profile_id, "cherry")
    review(client, remembered, "remembered")
    review(client, again, "remembered")
    review(client, again, "again")  # the latest answer counts

    deck = client.get("/api/reviews/deck").json()

    assert [card["id"] for card in deck] == [new, again, remembered]
    assert [card["last_outcome"] for card in deck] == [None, "again", "remembered"]


def test_card_front_uses_the_real_sentence_with_a_blank(
    client: TestClient, db_session: Session
) -> None:
    profile_id, conversation_id = make_profile(client, db_session)
    add_word(
        db_session,
        profile_id,
        "look after",
        source=(conversation_id, "She looks after her sister.", "looks after"),
    )
    add_word(db_session, profile_id, "book", example="Book a table, please.")

    cards = {card["lemma"]: card for card in client.get("/api/reviews/deck").json()}

    assert cards["look after"]["cloze"] == f"She {BLANK} her sister."
    assert cards["book"]["cloze"] == f"{BLANK} a table, please."


def test_vocabulary_can_be_filtered_by_review_status(
    client: TestClient, db_session: Session
) -> None:
    profile_id, _ = make_profile(client, db_session)
    reviewed = add_word(db_session, profile_id, "apple")
    add_word(db_session, profile_id, "banana")
    review(client, reviewed, "again")

    unreviewed = client.get("/api/vocabulary", params={"status": "unreviewed"}).json()
    done = client.get("/api/vocabulary", params={"status": "reviewed"}).json()

    assert [w["lemma"] for w in unreviewed] == ["banana"]
    assert [w["lemma"] for w in done] == ["apple"]


def test_review_page_shows_one_card_at_a_time_and_escapes(
    client: TestClient, db_session: Session
) -> None:
    profile_id, _ = make_profile(client, db_session)
    add_word(db_session, profile_id, "<b>apple</b>")
    add_word(db_session, profile_id, "banana")

    html = client.get("/review").text

    assert 'aria-current="page">Ôn tập</a>' in html
    assert html.count('class="flashcard"') == 2
    assert html.count("hidden>") >= 1  # later cards start hidden
    assert "Thẻ 1/2" in html
    assert "&lt;b&gt;apple&lt;/b&gt;" in html
    assert "<b>apple</b>" not in html


def test_review_page_without_words_explains_how_to_add_them(client: TestClient) -> None:
    html = client.get("/review").text

    assert "Chưa có từ để ôn" in html
