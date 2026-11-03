"""Domain logic for the append-only suggestion event log."""

from __future__ import annotations

from uuid import UUID

from app.features.events.repository import EventLogRepository
from app.models.suggestion_event import EventType, SuggestionEvent

__all__ = ["EventLogService"]


class EventLogService:
    """Records what happened to a suggestion; append-only by construction (D7) — no update or delete method exists."""

    def __init__(self, repository: EventLogRepository) -> None:
        """Bind the service to its append-only repository."""
        self._repo = repository

    def record(
        self,
        suggestion_id: UUID,
        event_type: EventType,
        *,
        data: dict | None = None,
        actor_user_id: UUID | None = None,
        actor_api_key_id: UUID | None = None,
    ) -> SuggestionEvent:
        """Append an event of the given type for a suggestion, attributed to the acting user or API key."""
        event = SuggestionEvent(
            suggestion_id=suggestion_id,
            event_type=event_type,
            data=data or {},
            actor_user_id=actor_user_id,
            actor_api_key_id=actor_api_key_id,
        )
        return self._repo.add(event)

    def list_for(self, suggestion_id: UUID) -> list[SuggestionEvent]:
        """Return the event history of a suggestion, oldest first."""
        return self._repo.list_for(suggestion_id)
