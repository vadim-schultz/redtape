"""Promoting an approved `new_requirement` suggestion into a real `DocumentRequirement` (Chapter 7)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.handlers import PromotionConflictError
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import SuggestionService
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.main import create_app
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def other_jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Otherland"}, code=f"O{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def taxonomy_service(db_session: Session) -> TaxonomyService:
    return TaxonomyService(TaxonomyRepository(db_session))


@pytest.fixture
def document_service(db_session: Session, taxonomy_service: TaxonomyService) -> DocumentService:
    return DocumentService(DocumentRepository(db_session), taxonomy_service)


@pytest.fixture
def event_log_service(db_session: Session) -> EventLogService:
    return EventLogService(EventLogRepository(db_session))


@pytest.fixture
def service(
    db_session: Session,
    document_service: DocumentService,
    taxonomy_service: TaxonomyService,
    event_log_service: EventLogService,
) -> SuggestionService:
    return SuggestionService(SuggestionRepository(db_session), document_service, taxonomy_service, event_log_service)


def _document(db_session: Session, jurisdiction: Jurisdiction, *, slug: str) -> Document:
    document = Document(jurisdiction_id=jurisdiction.id, slug=slug, title_i18n={"en": slug})
    db_session.add(document)
    db_session.flush()
    return document


def _requirement_suggestion(
    db_session: Session,
    jurisdiction: Jurisdiction,
    *,
    parent: Document,
    required: Document,
    notes_i18n: dict[str, str] | None = None,
) -> Suggestion:
    payload: dict[str, object] = {
        "parent_document_id": str(parent.id),
        "required_document_id": str(required.id),
    }
    if notes_i18n is not None:
        payload["notes_i18n"] = notes_i18n
    row = Suggestion(
        kind=SuggestionKind.NEW_REQUIREMENT,
        status=SuggestionStatus.PENDING,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        payload=payload,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _edge(db_session: Session, jurisdiction: Jurisdiction, parent: Document, required: Document) -> DocumentRequirement:
    stmt = select(DocumentRequirement).where(
        DocumentRequirement.jurisdiction_id == jurisdiction.id,
        DocumentRequirement.parent_document_id == parent.id,
        DocumentRequirement.required_document_id == required.id,
    )
    return db_session.scalar(stmt)


def test_approving_a_new_requirement_suggestion_creates_a_document_requirement(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    parent = _document(db_session, jurisdiction, slug="passport-application")
    required = _document(db_session, jurisdiction, slug="birth-certificate")
    suggestion = _requirement_suggestion(db_session, jurisdiction, parent=parent, required=required)

    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    edge = _edge(db_session, jurisdiction, parent, required)
    assert edge is not None
    assert edge.source == "community"


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_the_created_edge_appears_in_the_parent_documents_requirements(
    client: TestClient[Litestar], service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    parent = _document(db_session, jurisdiction, slug="passport-application")
    required = _document(db_session, jurisdiction, slug="birth-certificate")
    suggestion = _requirement_suggestion(db_session, jurisdiction, parent=parent, required=required)

    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    response = client.get(f"/api/v1/documents/{parent.id}")

    assert response.status_code == 200
    required_ids = [req["required_document"]["id"] for req in response.json()["requirements"]]
    assert str(required.id) in required_ids


def test_promotion_re_validates_both_documents_still_exist(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    parent = _document(db_session, jurisdiction, slug="passport-application")
    required = _document(db_session, jurisdiction, slug="birth-certificate")
    suggestion = _requirement_suggestion(db_session, jurisdiction, parent=parent, required=required)
    db_session.delete(required)
    db_session.flush()

    with pytest.raises(PromotionConflictError):
        service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    assert suggestion.status == SuggestionStatus.PENDING


def test_promotion_re_validates_the_jurisdiction_match(
    service: SuggestionService,
    db_session: Session,
    jurisdiction: Jurisdiction,
    other_jurisdiction: Jurisdiction,
) -> None:
    parent = _document(db_session, jurisdiction, slug="passport-application")
    required = _document(db_session, jurisdiction, slug="birth-certificate")
    suggestion = _requirement_suggestion(db_session, jurisdiction, parent=parent, required=required)
    required.jurisdiction_id = other_jurisdiction.id
    db_session.flush()

    with pytest.raises(PromotionConflictError):
        service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    assert suggestion.status == SuggestionStatus.PENDING


def test_promotion_rejects_a_duplicate_edge_that_appeared_after_submission(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    parent = _document(db_session, jurisdiction, slug="passport-application")
    required = _document(db_session, jurisdiction, slug="birth-certificate")
    suggestion = _requirement_suggestion(db_session, jurisdiction, parent=parent, required=required)
    db_session.add(
        DocumentRequirement(
            parent_document_id=parent.id, required_document_id=required.id, jurisdiction_id=jurisdiction.id
        )
    )
    db_session.flush()

    with pytest.raises(PromotionConflictError):
        service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    stmt = select(DocumentRequirement).where(
        DocumentRequirement.jurisdiction_id == jurisdiction.id,
        DocumentRequirement.parent_document_id == parent.id,
        DocumentRequirement.required_document_id == required.id,
    )
    assert len(db_session.scalars(stmt).all()) == 1
    assert suggestion.status == SuggestionStatus.PENDING


def _payload_for(kind: SuggestionKind, *, parent: Document, required: Document) -> dict[str, object]:
    if kind == SuggestionKind.NEW_DOCUMENT:
        return {"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"}
    return {"parent_document_id": str(parent.id), "required_document_id": str(required.id)}


@pytest.mark.parametrize("kind", list(SuggestionKind))
def test_kind_handlers_both_promote_without_not_implemented_error(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction, kind: SuggestionKind
) -> None:
    parent = _document(db_session, jurisdiction, slug="passport-application")
    required = _document(db_session, jurisdiction, slug="birth-certificate")
    suggestion = Suggestion(
        kind=kind,
        status=SuggestionStatus.PENDING,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        payload=_payload_for(kind, parent=parent, required=required),
    )
    db_session.add(suggestion)
    db_session.flush()

    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    assert suggestion.status == SuggestionStatus.APPROVED
