"""Queries for saved vocabulary (FR06)."""

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.models import Vocabulary, VocabularySource


class VocabularyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find(self, profile_id: int, lemma: str, meaning_key: str) -> Vocabulary | None:
        return self._session.scalar(
            select(Vocabulary).where(
                Vocabulary.profile_id == profile_id,
                Vocabulary.lemma == lemma,
                Vocabulary.meaning_key == meaning_key,
            )
        )

    def get(self, word_id: int) -> Vocabulary | None:
        return self._session.get(Vocabulary, word_id)

    def add(self, word: Vocabulary) -> Vocabulary:
        """Insert a word. Raises IntegrityError if the same word+meaning exists."""
        self._session.add(word)
        self._session.flush()
        return word

    def add_source(
        self,
        vocabulary_id: int,
        message_id: int,
        source_sentence: str,
        selected_start: int,
        selected_end: int,
    ) -> None:
        """Link a sentence to a word; saving the same place twice adds nothing."""
        statement = (
            insert(VocabularySource)
            .values(
                vocabulary_id=vocabulary_id,
                message_id=message_id,
                source_sentence=source_sentence,
                selected_start=selected_start,
                selected_end=selected_end,
            )
            .on_conflict_do_nothing()
        )
        self._session.execute(statement)

    def search(self, profile_id: int, query: str | None) -> list[Vocabulary]:
        """Newest first; `query` matches the word, its base form, meaning or note."""
        statement = (
            select(Vocabulary)
            .where(Vocabulary.profile_id == profile_id)
            .options(selectinload(Vocabulary.sources))
            .order_by(Vocabulary.created_at.desc(), Vocabulary.id.desc())
        )
        if query:
            # Parameterized ILIKE: wildcards in the query are escaped by autoescape.
            statement = statement.where(
                or_(
                    Vocabulary.lemma.icontains(query, autoescape=True),
                    Vocabulary.selected_text.icontains(query, autoescape=True),
                    Vocabulary.meaning_vi.icontains(query, autoescape=True),
                    Vocabulary.note.icontains(query, autoescape=True),
                )
            )
        return list(self._session.scalars(statement))

    def delete(self, word: Vocabulary) -> None:
        self._session.delete(word)
        self._session.flush()
