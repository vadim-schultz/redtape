"""Persistence for votes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.suggestion_vote import UQ_USER, SuggestionVote


class VoteRepository:
    """Persistence for votes; the session only."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, *, suggestion_id: UUID, user_id: UUID, value: int) -> SuggestionVote:
        stmt = (
            insert(SuggestionVote)
            .values(suggestion_id=suggestion_id, user_id=user_id, value=value)
            .on_conflict_do_update(constraint=UQ_USER, set_={"value": value})
            .returning(SuggestionVote)
        )
        return self._session.scalars(stmt).one()

    def delete(self, *, suggestion_id: UUID, user_id: UUID) -> None:
        stmt = delete(SuggestionVote).where(
            SuggestionVote.suggestion_id == suggestion_id, SuggestionVote.user_id == user_id
        )
        self._session.execute(stmt)

    def get(self, *, suggestion_id: UUID, user_id: UUID) -> SuggestionVote | None:
        stmt = select(SuggestionVote).where(
            SuggestionVote.suggestion_id == suggestion_id, SuggestionVote.user_id == user_id
        )
        return self._session.scalar(stmt)
