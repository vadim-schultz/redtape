"""Persistence for votes."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.suggestion_vote import UQ_USER, SuggestionVote
from app.schema.suggestion.read import Tally


def _tally(up: int, down: int) -> Tally:
    return Tally(up=up, down=down, score=up - down)


class VoteRepository:
    """Persistence for votes; the session only."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to the session it writes votes through."""
        self._session = session

    def upsert(self, *, suggestion_id: UUID, user_id: UUID, value: int) -> SuggestionVote:
        """Insert or update the caller's vote on a suggestion, returning the stored row."""
        stmt = (
            insert(SuggestionVote)
            .values(suggestion_id=suggestion_id, user_id=user_id, value=value)
            .on_conflict_do_update(constraint=UQ_USER, set_={"value": value})
            .returning(SuggestionVote)
        )
        return self._session.scalars(stmt).one()

    def delete(self, *, suggestion_id: UUID, user_id: UUID) -> None:
        """Delete the caller's vote on a suggestion, if one exists."""
        stmt = delete(SuggestionVote).where(
            SuggestionVote.suggestion_id == suggestion_id, SuggestionVote.user_id == user_id
        )
        self._session.execute(stmt)

    def get(self, *, suggestion_id: UUID, user_id: UUID) -> SuggestionVote | None:
        """Return the caller's vote on a suggestion, or None if there is none."""
        stmt = select(SuggestionVote).where(
            SuggestionVote.suggestion_id == suggestion_id, SuggestionVote.user_id == user_id
        )
        return self._session.scalar(stmt)

    def tally_for(self, suggestion_id: UUID) -> Tally:
        """Return the up, down and net tally of one suggestion's votes."""
        stmt = (
            select(SuggestionVote.value, func.count())
            .where(SuggestionVote.suggestion_id == suggestion_id)
            .group_by(SuggestionVote.value)
        )
        counts: dict[int, int] = dict(self._session.execute(stmt).tuples().all())
        return _tally(up=counts.get(1, 0), down=counts.get(-1, 0))

    def tally_for_many(self, suggestion_ids: Sequence[UUID]) -> dict[UUID, Tally]:
        """Return the tally of each suggestion in one query; a suggestion without votes gets a zero tally."""
        if not suggestion_ids:
            return {}
        stmt = (
            select(SuggestionVote.suggestion_id, SuggestionVote.value, func.count())
            .where(SuggestionVote.suggestion_id.in_(suggestion_ids))
            .group_by(SuggestionVote.suggestion_id, SuggestionVote.value)
        )
        counts: dict[UUID, dict[int, int]] = {}
        for suggestion_id, value, n in self._session.execute(stmt).all():
            counts.setdefault(suggestion_id, {})[value] = n
        return {
            sid: _tally(up=counts.get(sid, {}).get(1, 0), down=counts.get(sid, {}).get(-1, 0)) for sid in suggestion_ids
        }
