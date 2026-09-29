from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import AlreadyDecidedError, SuggestionService
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
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
def service(db_session: Session) -> SuggestionService:
    documents = DocumentService(DocumentRepository(db_session), TaxonomyService(TaxonomyRepository(db_session)))
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    return SuggestionService(SuggestionRepository(db_session), documents, taxonomy)


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
