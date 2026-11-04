"""Promoting an approved `new_document` suggestion into a real `Document` (Chapter 6)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from app.features.documents.promotion import DocumentPromotion
from app.features.documents.repository import DocumentRepository
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.handlers import PromotionConflictError
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import AlreadyDecidedError, SuggestionService
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.main import create_app
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_event import EventType
from app.schema.suggestion.payload import NewDocumentPayload
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session

from suggestion_support import compose_suggestion_service


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def taxonomy_service(db_session: Session) -> TaxonomyService:
    seed_taxonomy(db_session)
    return TaxonomyService(TaxonomyRepository(db_session))


@pytest.fixture
def document_promotion(db_session: Session, taxonomy_service: TaxonomyService) -> DocumentPromotion:
    return DocumentPromotion(DocumentRepository(db_session), taxonomy_service)


@pytest.fixture
def event_log_service(db_session: Session) -> EventLogService:
    return EventLogService(EventLogRepository(db_session))


@pytest.fixture
def service(
    db_session: Session,
    document_promotion: DocumentPromotion,
    taxonomy_service: TaxonomyService,
    event_log_service: EventLogService,
) -> SuggestionService:
    return compose_suggestion_service(
        SuggestionRepository(db_session), document_promotion, taxonomy_service, event_log_service
    )


def _suggestion(
    db_session: Session,
    jurisdiction: Jurisdiction,
    *,
    status: SuggestionStatus = SuggestionStatus.PENDING,
    title: str = "Residency permit",
    description: str | None = "How to register your residency.",
    official_url: str | None = "https://example.gov/residency",
    domain_codes: list[str] | None = None,
    situation_codes: list[str] | None = None,
) -> Suggestion:
    payload: dict[str, object] = {"title_i18n": {"en": title}}
    if official_url is not None:
        payload["official_url"] = official_url
    if description is not None:
        payload["description_i18n"] = {"en": description}
    if domain_codes is not None:
        payload["domain_codes"] = domain_codes
    if situation_codes is not None:
        payload["situation_codes"] = situation_codes
    row = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=status,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        payload=payload,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _document_by_slug(db_session: Session, jurisdiction: Jurisdiction, slug: str) -> Document | None:
    stmt = select(Document).where(Document.jurisdiction_id == jurisdiction.id, Document.slug == slug)
    return db_session.scalar(stmt)


def test_approving_a_new_document_suggestion_creates_a_document_with_its_fields(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, title="Residency permit", description="How to register.")

    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    document = _document_by_slug(db_session, jurisdiction, "residency-permit")
    assert document is not None
    assert document.title_i18n == {"en": "Residency permit"}
    assert document.description_i18n == {"en": "How to register."}
    assert document.official_url == "https://example.gov/residency"


def test_a_url_less_document_promotes_with_a_null_official_url(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, title="Personalausweis", official_url=None)

    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    document = _document_by_slug(db_session, jurisdiction, "personalausweis")
    assert document is not None
    assert document.official_url is None


def test_a_url_less_suggestion_racing_for_a_taken_slug_fails_on_the_slug_alone(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    first = _suggestion(db_session, jurisdiction, title="Personalausweis", official_url=None)
    second = _suggestion(db_session, jurisdiction, title="Personalausweis", official_url=None)
    service.transition_to(first.id, SuggestionStatus.APPROVED, actor=None)

    with pytest.raises(PromotionConflictError):
        service.transition_to(second.id, SuggestionStatus.APPROVED, actor=None)

    assert second.status == SuggestionStatus.PENDING


def test_promoting_a_new_document_suggestion_logs_a_promoted_event_with_the_created_document_id(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction, event_log_service: EventLogService
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, title="Residency permit")

    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    document = _document_by_slug(db_session, jurisdiction, "residency-permit")
    assert document is not None
    promoted = [e for e in event_log_service.list_for(suggestion.id) if e.event_type == EventType.PROMOTED]
    assert len(promoted) == 1
    assert promoted[0].data == {"created_id": str(document.id), "table": "document"}


def test_promote_resolves_domain_and_situation_codes_onto_the_created_document(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction, taxonomy_service: TaxonomyService
) -> None:
    suggestion = _suggestion(
        db_session,
        jurisdiction,
        title="Residency permit",
        domain_codes=["housing"],
        situation_codes=["moving-house"],
    )

    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    document = _document_by_slug(db_session, jurisdiction, "residency-permit")
    assert document is not None
    assert [d.code for d in document.domains] == ["housing"]
    assert [s.code for s in document.life_situations] == ["moving-house"]


def test_create_document_uses_the_given_slug_not_a_recomputed_one(
    document_promotion: DocumentPromotion, jurisdiction: Jurisdiction
) -> None:
    payload = NewDocumentPayload(title_i18n={"en": "Residency permit"}, official_url="https://example.gov/residency")

    document = document_promotion.create_document(payload, jurisdiction.id, "a-totally-different-slug")

    assert document.slug == "a-totally-different-slug"


def test_a_second_suggestion_racing_for_the_same_slug_fails_without_corrupting_either_row(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    first = _suggestion(db_session, jurisdiction, title="Residency permit", official_url="https://example.gov/first")
    second = _suggestion(db_session, jurisdiction, title="Residency permit", official_url="https://example.gov/second")

    service.transition_to(first.id, SuggestionStatus.APPROVED, actor=None)

    with pytest.raises(PromotionConflictError):
        service.transition_to(second.id, SuggestionStatus.APPROVED, actor=None)

    assert second.status == SuggestionStatus.PENDING
    stmt = select(Document).where(Document.jurisdiction_id == jurisdiction.id, Document.slug == "residency-permit")
    assert len(db_session.scalars(stmt).all()) == 1


def test_approving_twice_is_prevented_by_already_decided_not_a_duplicate_document(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, title="Residency permit")
    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    with pytest.raises(AlreadyDecidedError):
        service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)

    stmt = select(Document).where(Document.jurisdiction_id == jurisdiction.id, Document.slug == "residency-permit")
    assert len(db_session.scalars(stmt).all()) == 1


def test_a_rejected_suggestion_never_creates_a_document(
    service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, title="Residency permit")

    service.transition_to(suggestion.id, SuggestionStatus.REJECTED, actor=None)

    assert _document_by_slug(db_session, jurisdiction, "residency-permit") is None


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_the_created_document_is_retrievable_through_the_existing_documents_endpoint(
    client: TestClient[Litestar], service: SuggestionService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, title="Residency permit")
    service.transition_to(suggestion.id, SuggestionStatus.APPROVED, actor=None)
    document = _document_by_slug(db_session, jurisdiction, "residency-permit")
    assert document is not None

    response = client.get(f"/api/v1/documents/{document.id}")

    assert response.status_code == 200
    assert response.json()["slug"] == "residency-permit"
