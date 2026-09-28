"""Persistence for suggestions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.suggestion import Suggestion


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
