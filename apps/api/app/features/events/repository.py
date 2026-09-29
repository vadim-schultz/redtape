"""Persistence for suggestion events."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.suggestion_event import SuggestionEvent


class EventLogRepository:
    """Persistence for suggestion events; the session only. Append and read, nothing else."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: SuggestionEvent) -> SuggestionEvent:
        self._session.add(event)
        self._session.flush()
        return event

    def list_for(self, suggestion_id: UUID) -> list[SuggestionEvent]:
        stmt = (
            select(SuggestionEvent)
            .where(SuggestionEvent.suggestion_id == suggestion_id)
            .order_by(SuggestionEvent.created_at, SuggestionEvent.id)
        )
        return list(self._session.scalars(stmt).all())
