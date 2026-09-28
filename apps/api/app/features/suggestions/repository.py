"""Persistence for suggestions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.suggestion import Suggestion, SuggestionKind, SuggestionStatus


class SuggestionRepository:
    """Persistence for suggestions; the session only."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, suggestion: Suggestion) -> Suggestion:
        self._session.add(suggestion)
        self._session.flush()
        return suggestion

    def get(self, suggestion_id: UUID) -> Suggestion | None:
        return self._session.get(Suggestion, suggestion_id)

    def find_pending_by_url(self, *, jurisdiction_id: UUID, normalized_url: str) -> list[UUID]:
        """Ids of pending `new_document` suggestions in `jurisdiction_id` with this normalized URL."""
        stmt = select(Suggestion.id).where(
            Suggestion.jurisdiction_id == jurisdiction_id,
            Suggestion.normalized_url == normalized_url,
            Suggestion.status == SuggestionStatus.PENDING,
            Suggestion.kind == SuggestionKind.NEW_DOCUMENT,
        )
        return list(self._session.scalars(stmt).all())
