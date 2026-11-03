"""Dependency providers for the events feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService


def provide_event_log_repository(session: Session) -> EventLogRepository:
    """Bind an event log repository to the request session."""
    return EventLogRepository(session)


def provide_event_log_service(event_log_repository: EventLogRepository) -> EventLogService:
    """Bind the event log service to its repository."""
    return EventLogService(event_log_repository)


router_dependencies = {
    "event_log_repository": Provide(provide_event_log_repository, sync_to_thread=False),
    "event_log_service": Provide(provide_event_log_service, sync_to_thread=False),
}
