from __future__ import annotations

import uuid

import pytest
from app.features.documents.promotion import DocumentPromotion
from app.features.documents.repository import DocumentRepository
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import AlreadyDecidedError, SuggestionNotFoundError, SuggestionService
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.user import AppUser
from sqlalchemy import event, update
from sqlalchemy.orm import Session

from suggestion_support import compose_suggestion_service


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
def event_log_service(db_session: Session) -> EventLogService:
    return EventLogService(EventLogRepository(db_session))


@pytest.fixture
def service(db_session: Session, event_log_service: EventLogService) -> SuggestionService:
    documents = DocumentPromotion(DocumentRepository(db_session))
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    return compose_suggestion_service(SuggestionRepository(db_session), documents, taxonomy, event_log_service)


def _suggestion(
    session: Session,
    jurisdiction: Jurisdiction,
    submitter: AppUser,
    status: SuggestionStatus = SuggestionStatus.PENDING,
) -> Suggestion:
    row = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=status,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        submitted_by_user_id=submitter.id,
        payload={"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"},
    )
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def pending_suggestion(db_session: Session, jurisdiction: Jurisdiction, submitter: AppUser) -> Suggestion:
    return _suggestion(db_session, jurisdiction, submitter)


def test_transition_to_pending_to_approved_changes_the_status_column(
    service: SuggestionService, pending_suggestion: Suggestion
) -> None:
    service.transition_to(pending_suggestion.id, SuggestionStatus.APPROVED, actor=None)

    assert pending_suggestion.status == SuggestionStatus.APPROVED


def test_transition_to_pending_to_pending_is_a_noop(service: SuggestionService, pending_suggestion: Suggestion) -> None:
    service.transition_to(pending_suggestion.id, SuggestionStatus.PENDING, actor=None)

    assert pending_suggestion.status == SuggestionStatus.PENDING


def test_transition_to_approved_to_anything_raises_already_decided(
    db_session: Session, service: SuggestionService, jurisdiction: Jurisdiction, submitter: AppUser
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, submitter, status=SuggestionStatus.APPROVED)

    with pytest.raises(AlreadyDecidedError):
        service.transition_to(suggestion.id, SuggestionStatus.REJECTED, actor=None)


def test_transition_to_rejected_to_anything_raises_already_decided(
    db_session: Session, service: SuggestionService, jurisdiction: Jurisdiction, submitter: AppUser
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, submitter, status=SuggestionStatus.REJECTED)

    with pytest.raises(AlreadyDecidedError):
        service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)


def test_transition_to_logs_a_status_changed_event_with_from_and_to(
    service: SuggestionService, event_log_service: EventLogService, pending_suggestion: Suggestion
) -> None:
    service.transition_to(pending_suggestion.id, SuggestionStatus.REJECTED, actor=None)

    changed = [e for e in event_log_service.list_for(pending_suggestion.id) if e.event_type == EventType.STATUS_CHANGED]
    assert len(changed) == 1
    assert changed[0].data == {"from": "pending", "to": "rejected"}


def test_transition_to_an_automatic_transition_logs_no_actor(
    service: SuggestionService, event_log_service: EventLogService, pending_suggestion: Suggestion
) -> None:
    service.transition_to(pending_suggestion.id, SuggestionStatus.REJECTED, actor=None)

    changed = next(
        e for e in event_log_service.list_for(pending_suggestion.id) if e.event_type == EventType.STATUS_CHANGED
    )
    assert changed.actor_user_id is None
    assert changed.actor_api_key_id is None


def test_transition_to_an_unknown_suggestion_raises_suggestion_not_found(service: SuggestionService) -> None:
    assert issubclass(SuggestionNotFoundError, ValueError)

    with pytest.raises(SuggestionNotFoundError):
        service.transition_to(uuid.uuid4(), SuggestionStatus.APPROVED, actor=None)


def test_transition_reads_the_pending_row_with_for_update(
    db_session: Session, service: SuggestionService, pending_suggestion: Suggestion
) -> None:
    statements: list[str] = []

    def _capture(
        conn: object, cursor: object, statement: str, parameters: object, context: object, executemany: bool
    ) -> None:
        statements.append(statement)

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", _capture)
    try:
        service.transition_to(pending_suggestion.id, SuggestionStatus.REJECTED, actor=None)
    finally:
        event.remove(bind, "before_cursor_execute", _capture)

    assert any("SUGGESTION" in s.upper() and "FOR UPDATE" in s.upper() for s in statements)


def test_transition_sees_a_status_changed_behind_the_identity_map(
    db_session: Session, service: SuggestionService, pending_suggestion: Suggestion
) -> None:
    # Load `pending_suggestion` into the identity map holding `PENDING`, then flip the column
    # underneath it with a Core statement so a stale read would miss the decision.
    db_session.get(Suggestion, pending_suggestion.id)
    db_session.execute(
        update(Suggestion).where(Suggestion.id == pending_suggestion.id).values(status=SuggestionStatus.APPROVED)
    )
    db_session.flush()

    with pytest.raises(AlreadyDecidedError):
        service.transition_to(pending_suggestion.id, SuggestionStatus.REJECTED, actor=None)
