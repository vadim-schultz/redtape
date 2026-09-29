"""Response schema for `GET /api/v1/suggestions/{id}/events` (Chapter 9)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.suggestion_event import EventType, SuggestionEvent


class EventRead(BaseModel):
    """One row of a suggestion's audit trail; actors are ids only, never emails or key hashes (D7)."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    event_type: EventType
    data: dict
    actor_user_id: UUID | None
    actor_api_key_id: UUID | None
    created_at: datetime

    @classmethod
    def from_row(cls, event: SuggestionEvent) -> EventRead:
        return cls(
            id=event.id,
            event_type=event.event_type,
            data=event.data,
            actor_user_id=event.actor_user_id,
            actor_api_key_id=event.actor_api_key_id,
            created_at=event.created_at,
        )
