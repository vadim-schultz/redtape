"""Discovery event and fetch-log persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryEvent, DiscoveryEventType, DiscoveryFetchLog, DiscoveryTask


@dataclass(frozen=True, slots=True)
class NewEvent:
    """A discovery event to record."""

    event_type: DiscoveryEventType
    catalogue_service_id: UUID | None = None
    discovery_task_id: UUID | None = None
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FetchLogEntry:
    """The outcome of one crawler fetch for a task."""

    discovery_task_id: UUID
    http_status: int | None
    content_type: str | None
    byte_length: int | None
    error_message: str | None
    fetched_at: datetime


class ActivityRepository(SessionRepository):
    """Record and list discovery events and fetch logs."""

    def record_event(self, event: NewEvent) -> DiscoveryEvent:
        """Persist ``event`` and return the row."""
        row = DiscoveryEvent(
            event_type=event.event_type,
            catalogue_service_id=event.catalogue_service_id,
            discovery_task_id=event.discovery_task_id,
            payload=event.payload,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def append_fetch_log(self, entry: FetchLogEntry) -> DiscoveryFetchLog:
        """Persist ``entry`` and return the row."""
        row = DiscoveryFetchLog(
            discovery_task_id=entry.discovery_task_id,
            http_status=entry.http_status,
            content_type=entry.content_type,
            byte_length=entry.byte_length,
            error_message=entry.error_message,
            fetched_at=entry.fetched_at,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_catalogue_events(self, catalogue_id: UUID) -> list[DiscoveryEvent]:
        """Return the events of one catalogue row, oldest first."""
        stmt = (
            select(DiscoveryEvent)
            .where(DiscoveryEvent.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryEvent.created_at.asc(), DiscoveryEvent.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_catalogue_fetch_logs(self, catalogue_id: UUID) -> list[DiscoveryFetchLog]:
        """Return the fetch logs of one catalogue row, oldest first."""
        stmt = (
            select(DiscoveryFetchLog)
            .join(DiscoveryTask, DiscoveryFetchLog.discovery_task_id == DiscoveryTask.id)
            .where(DiscoveryTask.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryFetchLog.fetched_at.asc(), DiscoveryFetchLog.id.asc())
        )
        return list(self._session.scalars(stmt).all())
