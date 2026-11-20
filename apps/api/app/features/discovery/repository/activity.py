"""Discovery event and fetch-log persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryEvent, DiscoveryEventType, DiscoveryFetchLog, DiscoveryTask, DiscoveryTaskKind


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
    body_sha256: str | None = None


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
            body_sha256=entry.body_sha256,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def last_body_sha256(self, *, catalogue_service_id: UUID, kind: DiscoveryTaskKind, target_url: str) -> str | None:
        """Return the body hash of the newest fetch of the page that recorded one, or ``None`` when none did.

        The page is the catalogue row, kind and target URL. Its tasks differ by input key (a refresh is a new task),
        so the comparison is with the page's last body whichever task fetched it.
        """
        stmt = (
            select(DiscoveryFetchLog.body_sha256)
            .join(DiscoveryTask, DiscoveryFetchLog.discovery_task_id == DiscoveryTask.id)
            .where(
                DiscoveryTask.catalogue_service_id == catalogue_service_id,
                DiscoveryTask.kind == kind,
                DiscoveryTask.target_url == target_url,
                DiscoveryFetchLog.body_sha256.is_not(None),
            )
            .order_by(DiscoveryFetchLog.fetched_at.desc(), DiscoveryFetchLog.id.desc())
            .limit(1)
        )
        return self._session.scalar(stmt)

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

    def catalogue_has_fetch_log(self, catalogue_id: UUID) -> bool:
        """Return whether any task of one catalogue row has a fetch log."""
        stmt = select(
            select(DiscoveryFetchLog.id)
            .join(DiscoveryTask, DiscoveryFetchLog.discovery_task_id == DiscoveryTask.id)
            .where(DiscoveryTask.catalogue_service_id == catalogue_id)
            .exists()
        )
        return bool(self._session.scalar(stmt))
