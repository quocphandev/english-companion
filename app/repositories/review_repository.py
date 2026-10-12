"""Queries for flashcard review (FR07)."""

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import ReviewEvent, Vocabulary


class ReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, vocabulary_id: int, outcome: str) -> ReviewEvent:
        event = ReviewEvent(vocabulary_id=vocabulary_id, outcome=outcome)
        self._session.add(event)
        self._session.flush()
        self._session.refresh(event)
        return event

    def deck(self, profile_id: int, limit: int) -> list[tuple[Vocabulary, str | None]]:
        """Words to review with their last outcome, in this order:
        never reviewed, then "again" (not remembered), then remembered,
        each group oldest review first.
        """
        latest = select(
            ReviewEvent.vocabulary_id,
            ReviewEvent.outcome,
            ReviewEvent.reviewed_at,
            func.row_number()
            .over(
                partition_by=ReviewEvent.vocabulary_id,
                order_by=(ReviewEvent.reviewed_at.desc(), ReviewEvent.id.desc()),
            )
            .label("rank"),
        ).subquery()
        group = case(
            (latest.c.outcome.is_(None), 0),
            (latest.c.outcome == "again", 1),
            else_=2,
        )
        statement = (
            select(Vocabulary, latest.c.outcome)
            .outerjoin(
                latest,
                and_(latest.c.vocabulary_id == Vocabulary.id, latest.c.rank == 1),
            )
            .where(Vocabulary.profile_id == profile_id)
            .options(selectinload(Vocabulary.sources))
            .order_by(group, latest.c.reviewed_at.asc().nulls_first(), Vocabulary.id)
            .limit(limit)
        )
        return [(word, outcome) for word, outcome in self._session.execute(statement)]
