"""FR07 (MVP): manual flashcards with "Nhớ" / "Chưa nhớ".

The spaced schedule (review again after 1, 3, 7, 14, 30 days) is phase 3.
"""

import re

from sqlalchemy.orm import Session

from app.models import Vocabulary
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.vocabulary_repository import VocabularyRepository
from app.schemas.review import Flashcard, ReviewIn, ReviewOut
from app.services.vocabulary_service import word_not_found

BLANK = "____"
DECK_SIZE = 20


def make_cloze(sentence: str, start: int, end: int) -> str:
    """The sentence with the selection [start, end) replaced by a blank."""
    return f"{sentence[:start]}{BLANK}{sentence[end:]}"


def cloze_from_example(example: str, words: list[str]) -> str | None:
    """Blank the first whole-word match of any of `words` in the example, if found."""
    for word in words:
        pattern = re.compile(rf"(?<!\w){re.escape(word)}(?!\w)", re.IGNORECASE)
        if pattern.search(example):
            return pattern.sub(BLANK, example, count=1)
    return None


def flashcard_cloze(word: Vocabulary) -> str | None:
    """Prefer the real sentence the word was met in; else blank it in the example."""
    if word.sources:
        source = word.sources[-1]
        return make_cloze(
            source.source_sentence, source.selected_start, source.selected_end
        )
    return cloze_from_example(word.example_en, [word.selected_text, word.lemma])


class ReviewService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._reviews = ReviewRepository(session)
        self._words = VocabularyRepository(session)
        self._conversations = ConversationRepository(session)

    def record(self, request: ReviewIn) -> ReviewOut:
        if self._words.get(request.vocabulary_id) is None:
            raise word_not_found()
        event = self._reviews.add(request.vocabulary_id, request.outcome)
        self._session.commit()
        return ReviewOut(
            vocabulary_id=event.vocabulary_id,
            outcome=event.outcome,
            reviewed_at=event.reviewed_at,
        )

    def deck(self, limit: int = DECK_SIZE) -> list[Flashcard]:
        profile = self._conversations.get_or_create_default_profile()
        return [
            Flashcard(
                id=word.id,
                lemma=word.lemma,
                selected_text=word.selected_text,
                pos=word.pos,
                meaning_vi=word.meaning_vi,
                example_en=word.example_en,
                cloze=flashcard_cloze(word),
                last_outcome=outcome,
            )
            for word, outcome in self._reviews.deck(profile.id, limit)
        ]
