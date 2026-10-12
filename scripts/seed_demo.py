"""Add a small demo conversation and a few saved words, without calling the AI.

Usage:  python -m scripts.seed_demo

Writes to DATABASE_URL. Only adds rows: nothing is deleted or changed. Running it
again does nothing if the demo conversation already exists.
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_engine
from app.models import (
    Conversation,
    Correction,
    Message,
    ReviewEvent,
    Vocabulary,
    VocabularySource,
)
from app.repositories.conversation_repository import ConversationRepository
from app.services.vocabulary_service import meaning_key, normalize_lemma

DEMO_TOPIC = "Demo: a weekend trip"
DEMO_PROMPT_VERSION = "demo-seed"

# (user text, corrections, chatbot reply)
TURNS: list[tuple[str, list[dict[str, str]], str]] = [
    (
        "Last weekend I go to Da Lat with my family.",
        [
            {
                "category": "grammar",
                "original_span": "I go",
                "corrected_text": "I went",
                "explanation_vi": "Chuyện đã xảy ra (last weekend) dùng quá khứ đơn.",
            }
        ],
        "That sounds lovely! Did you book a hotel, or did you stay with friends?",
    ),
    (
        "We stayed in a small hotel near the lake.",
        [],
        (
            "Nice choice. The weather in Da Lat is cool. Who looks after your pets "
            "when you travel?"
        ),
    ),
]

# (selected text, lemma, pos, meaning_vi, example_en, reply index)
WORDS: list[tuple[str, str, str, str, str, int]] = [
    ("book", "book", "verb", "đặt (phòng, vé)", "I booked a table for two.", 0),
    (
        "looks after",
        "look after",
        "phrasal verb",
        "chăm sóc, trông nom",
        "My sister looks after my cat.",
        1,
    ),
]


def seed_demo(session: Session) -> int | None:
    """Create the demo data; return the new conversation id, or None if it exists."""
    exists = session.scalar(
        select(Conversation.id).where(Conversation.topic == DEMO_TOPIC)
    )
    if exists is not None:
        return None
    profile = ConversationRepository(session).get_or_create_default_profile()
    conversation = Conversation(
        profile_id=profile.id,
        topic=DEMO_TOPIC,
        level="A2",
        correction_mode="learning",
    )
    session.add(conversation)
    session.flush()

    session.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            original_text="Hi! Tell me about your last weekend. Where did you go?",
            status="succeeded",
        )
    )
    replies = [add_turn(session, conversation.id, *turn) for turn in TURNS]
    for selected, lemma, pos, meaning, example, reply_index in WORDS:
        add_word(
            session,
            profile.id,
            replies[reply_index],
            selected,
            lemma,
            pos,
            meaning,
            example,
        )
    session.commit()
    return conversation.id


def add_turn(
    session: Session,
    conversation_id: int,
    text: str,
    corrections: list[dict[str, str]],
    reply_text: str,
) -> Message:
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        original_text=text,
        status="succeeded",
    )
    session.add(user_message)
    session.flush()
    for correction in corrections:
        session.add(
            Correction(
                message_id=user_message.id,
                prompt_version=DEMO_PROMPT_VERSION,
                **correction,
            )
        )
    reply = Message(
        conversation_id=conversation_id,
        role="assistant",
        original_text=reply_text,
        status="succeeded",
        reply_to_message_id=user_message.id,
    )
    session.add(reply)
    session.flush()
    return reply


def add_word(
    session: Session,
    profile_id: int,
    reply: Message,
    selected: str,
    lemma: str,
    pos: str,
    meaning_vi: str,
    example_en: str,
) -> None:
    lemma = normalize_lemma(lemma)
    key = meaning_key(meaning_vi)
    word = session.scalar(
        select(Vocabulary).where(
            Vocabulary.profile_id == profile_id,
            Vocabulary.lemma == lemma,
            Vocabulary.meaning_key == key,
        )
    )
    if word is None:
        word = Vocabulary(
            profile_id=profile_id,
            lemma=lemma,
            selected_text=selected,
            meaning_vi=meaning_vi,
            meaning_key=key,
            pos=pos,
            example_en=example_en,
        )
        session.add(word)
        session.flush()
        # One answer already recorded, so the review page shows both groups.
        session.add(ReviewEvent(vocabulary_id=word.id, outcome="again"))
    start = reply.original_text.index(selected)
    session.add(
        VocabularySource(
            vocabulary_id=word.id,
            message_id=reply.id,
            source_sentence=reply.original_text,
            selected_start=start,
            selected_end=start + len(selected),
        )
    )


def main() -> int:
    with SessionLocal(bind=get_engine()) as session:
        conversation_id = seed_demo(session)
    if conversation_id is None:
        print("Demo data already exists; nothing added.")
    else:
        print(f"Demo conversation created: /conversations/{conversation_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
