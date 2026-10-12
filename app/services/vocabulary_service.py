"""FR06: save looked-up words without duplicates, list, edit and delete them."""

import re
import unicodedata

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.harness.lookup_context import lookup_cache_key
from app.models import Vocabulary
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.lookup_repository import LookupRepository
from app.repositories.vocabulary_repository import VocabularyRepository
from app.schemas.ai import LookupReply
from app.schemas.vocabulary import (
    ReviewStatus,
    SaveWordIn,
    SaveWordResponse,
    SourceOut,
    UpdateWordIn,
    WordOut,
)
from app.services.lookup_service import message_not_found, selection_context

_PUNCTUATION = re.compile(r"[^\w\s]")
_SPACES = re.compile(r"\s+")


def normalize_lemma(lemma: str) -> str:
    """ "Look  After" -> "look after"."""
    return _SPACES.sub(" ", lemma).strip().lower()


def meaning_key(meaning_vi: str) -> str:
    """Normalized meaning for duplicate detection: case, spacing and punctuation
    are ignored; Vietnamese accents are kept ("đặt" and "dat" are different)."""
    text = unicodedata.normalize("NFC", meaning_vi).lower()
    text = _PUNCTUATION.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def lookup_required() -> AppError:
    return AppError(
        "lookup_required",
        "Hãy tra nghĩa từ này trước khi lưu.",
        http_status=status.HTTP_409_CONFLICT,
    )


def word_not_found() -> AppError:
    return AppError(
        "word_not_found",
        "Không tìm thấy từ này trong sổ từ.",
        http_status=status.HTTP_404_NOT_FOUND,
    )


def duplicate_meaning() -> AppError:
    return AppError(
        "duplicate_meaning",
        "Sổ từ đã có từ này với nghĩa đó.",
        http_status=status.HTTP_409_CONFLICT,
    )


class VocabularyService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._words = VocabularyRepository(session)
        self._lookups = LookupRepository(session)
        self._conversations = ConversationRepository(session)

    def save(self, request: SaveWordIn) -> SaveWordResponse:
        message = self._lookups.get_message(request.message_id)
        if message is None:
            raise message_not_found()
        # Re-read the sentence from the DB and reuse the verified (cached) lookup.
        context = selection_context(message.original_text, request.start, request.end)
        cached = self._lookups.find_cached(lookup_cache_key(context))
        if cached is None:
            raise lookup_required()
        lookup = LookupReply.model_validate(cached.result)
        profile_id = message.conversation.profile_id
        lemma = normalize_lemma(lookup.lemma)
        key = meaning_key(request.meaning_vi)

        word = self._words.find(profile_id, lemma, key)
        created = word is None
        if word is None:
            try:
                word = self._words.add(
                    Vocabulary(
                        profile_id=profile_id,
                        lemma=lemma,
                        selected_text=context.selected_text,
                        meaning_vi=request.meaning_vi,
                        meaning_key=key,
                        pos=lookup.pos,
                        example_en=lookup.example_en,
                    )
                )
            except IntegrityError:
                # Saved by a concurrent request: use that row instead.
                self._session.rollback()
                word = self._words.find(profile_id, lemma, key)
                if word is None:
                    raise
                created = False
        self._words.add_source(
            word.id, message.id, context.sentence, context.start, context.end
        )
        self._session.commit()
        self._session.refresh(word)
        return SaveWordResponse(created=created, word=to_word_out(word))

    def list_words(
        self, query: str | None = None, review_status: ReviewStatus | None = None
    ) -> list[WordOut]:
        profile = self._conversations.get_or_create_default_profile()
        words = self._words.search(profile.id, query, review_status)
        return [to_word_out(w) for w in words]

    def update(self, word_id: int, request: UpdateWordIn) -> WordOut:
        word = self._words.get(word_id)
        if word is None:
            raise word_not_found()
        if "note" in request.model_fields_set:
            word.note = request.note or None
        if request.meaning_vi is not None:
            key = meaning_key(request.meaning_vi)
            existing = self._words.find(word.profile_id, word.lemma, key)
            if existing is not None and existing.id != word.id:
                raise duplicate_meaning()
            word.meaning_vi = request.meaning_vi
            word.meaning_key = key
        self._session.commit()
        self._session.refresh(word)
        return to_word_out(word)

    def delete(self, word_id: int) -> None:
        word = self._words.get(word_id)
        if word is None:
            raise word_not_found()
        self._words.delete(word)
        self._session.commit()


def to_word_out(word: Vocabulary) -> WordOut:
    return WordOut(
        id=word.id,
        lemma=word.lemma,
        selected_text=word.selected_text,
        meaning_vi=word.meaning_vi,
        pos=word.pos,
        example_en=word.example_en,
        note=word.note,
        created_at=word.created_at,
        sources=[SourceOut.model_validate(s) for s in word.sources],
    )
