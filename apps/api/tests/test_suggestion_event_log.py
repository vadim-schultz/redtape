"""The append-only suggestion event log (Chapter 8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_event import EventType, SuggestionEvent
from app.models.user import AppUser
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def submitter(db_session: Session) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def pending_suggestion(db_session: Session, jurisdiction: Jurisdiction, submitter: AppUser) -> Suggestion:
    row = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=SuggestionStatus.PENDING,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        submitted_by_user_id=submitter.id,
        payload={"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"},
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def service(db_session: Session) -> EventLogService:
    return EventLogService(EventLogRepository(db_session))


def test_record_and_list_for_round_trip_an_event(service: EventLogService, pending_suggestion: Suggestion) -> None:
    service.record(pending_suggestion.id, EventType.VOTED, data={"value": 1})

    events = service.list_for(pending_suggestion.id)

    assert len(events) == 1
    assert events[0].event_type == EventType.VOTED
    assert events[0].data == {"value": 1}


def test_event_log_service_has_no_update_or_delete_method() -> None:
    public_methods = {
        name for name in vars(EventLogService) if not name.startswith("_") and callable(getattr(EventLogService, name))
    }

    assert public_methods == {"record", "list_for"}


def test_list_for_returns_events_in_chronological_order(
    db_session: Session, service: EventLogService, pending_suggestion: Suggestion
) -> None:
    now = datetime.now(UTC)
    older = SuggestionEvent(
        suggestion_id=pending_suggestion.id,
        event_type=EventType.SUBMITTED,
        data={},
        created_at=now - timedelta(minutes=2),
    )
    newer = SuggestionEvent(
        suggestion_id=pending_suggestion.id, event_type=EventType.VOTED, data={"value": 1}, created_at=now
    )
    db_session.add_all([newer, older])
    db_session.flush()

    events = service.list_for(pending_suggestion.id)

    assert [e.event_type for e in events] == [EventType.SUBMITTED, EventType.VOTED]


def test_list_for_an_unknown_suggestion_returns_an_empty_list_not_an_error(service: EventLogService) -> None:
    assert service.list_for(uuid.uuid4()) == []
