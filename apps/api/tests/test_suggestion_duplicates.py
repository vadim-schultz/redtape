"""Duplicate detection when creating a `new_document` suggestion (D4)."""

from __future__ import annotations

import uuid

import pytest
from app.features.documents.promotion import DocumentPromotion
from app.features.documents.repository import DocumentRepository
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import Conflict, DuplicateSuggestionError, SuggestionService
from app.features.suggestions.submitters import HumanSubmitter
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.user import AppUser
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload
from app.url_normalization import normalize_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}"
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


@pytest.fixture
def other_country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Otherland"}, code=f"T{uuid.uuid4().hex[:8]}"
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


@pytest.fixture
def user(db_session: Session) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def service(db_session: Session) -> SuggestionService:
    documents = DocumentPromotion(DocumentRepository(db_session), TaxonomyService(TaxonomyRepository(db_session)))
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    events = EventLogService(EventLogRepository(db_session))
    return SuggestionService(SuggestionRepository(db_session), documents, taxonomy, events)


def _document(
    db_session: Session,
    jurisdiction: Jurisdiction,
    *,
    slug: str = "residency-permit",
    official_url: str | None = "https://example.gov/residency",
) -> Document:
    doc = Document(
        jurisdiction_id=jurisdiction.id,
        slug=slug,
        title_i18n={"en": "Residency permit"},
        official_url=official_url,
    )
    db_session.add(doc)
    db_session.flush()
    return doc


def _pending_suggestion(
    db_session: Session,
    jurisdiction: Jurisdiction,
    *,
    normalized_url: str | None,
    status: SuggestionStatus = SuggestionStatus.PENDING,
) -> Suggestion:
    suggestion = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=status,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        payload={"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"},
        normalized_url=normalized_url,
    )
    db_session.add(suggestion)
    db_session.flush()
    return suggestion


def _payload(**overrides: object) -> NewDocumentPayload:
    defaults: dict[str, object] = {
        "title_i18n": {"en": "Residency permit"},
        "official_url": "https://example.gov/residency",
    }
    defaults.update(overrides)
    return NewDocumentPayload(**defaults)


def _request(jurisdiction: Jurisdiction, **overrides: object) -> SuggestionCreate:
    payload = overrides.pop("payload", _payload())
    return SuggestionCreate(payload=payload, jurisdiction_id=jurisdiction.id, **overrides)


def test_same_slug_in_the_same_jurisdiction_conflicts_with_the_document(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    document = _document(db_session, country, slug="residency-permit")
    request = _request(
        country,
        payload=_payload(title_i18n={"en": "Residency Permit"}, official_url="https://example.gov/a-different-page"),
    )

    with pytest.raises(DuplicateSuggestionError) as exc_info:
        service.create(submitter=HumanSubmitter(user.id), request=request)

    assert exc_info.value.conflicts == [Conflict("document", document.id)]


def test_same_normalized_official_url_conflicts_even_if_the_title_differs(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    document = _document(db_session, country, slug="other-slug", official_url="https://Example.gov/residency/")
    request = _request(
        country,
        payload=_payload(
            title_i18n={"en": "Something completely different"}, official_url="https://example.gov/residency"
        ),
    )

    with pytest.raises(DuplicateSuggestionError) as exc_info:
        service.create(submitter=HumanSubmitter(user.id), request=request)

    assert exc_info.value.conflicts == [Conflict("document", document.id)]


def test_same_slug_in_another_jurisdiction_is_allowed(
    service: SuggestionService, db_session: Session, country: Jurisdiction, other_country: Jurisdiction, user: AppUser
) -> None:
    _document(db_session, other_country, slug="residency-permit")
    request = _request(
        country,
        payload=_payload(title_i18n={"en": "Residency Permit"}, official_url="https://example.gov/unique-page"),
    )

    suggestion = service.create(submitter=HumanSubmitter(user.id), request=request).suggestion

    assert suggestion.status == SuggestionStatus.PENDING


def test_same_url_as_a_pending_suggestion_conflicts(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    pending = _pending_suggestion(db_session, country, normalized_url=normalize_url("https://example.gov/residency"))
    request = _request(country, payload=_payload(official_url="https://example.gov/residency"))

    with pytest.raises(DuplicateSuggestionError) as exc_info:
        service.create(submitter=HumanSubmitter(user.id), request=request)

    assert exc_info.value.conflicts == [Conflict("suggestion", pending.id)]


def test_same_url_as_an_approved_suggestion_is_allowed(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    _pending_suggestion(
        db_session,
        country,
        normalized_url=normalize_url("https://example.gov/residency"),
        status=SuggestionStatus.APPROVED,
    )
    request = _request(country, payload=_payload(official_url="https://example.gov/residency"))

    suggestion = service.create(submitter=HumanSubmitter(user.id), request=request).suggestion

    assert suggestion.status == SuggestionStatus.PENDING


def test_same_url_as_a_rejected_suggestion_is_allowed(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    _pending_suggestion(
        db_session,
        country,
        normalized_url=normalize_url("https://example.gov/residency"),
        status=SuggestionStatus.REJECTED,
    )
    request = _request(country, payload=_payload(official_url="https://example.gov/residency"))

    suggestion = service.create(submitter=HumanSubmitter(user.id), request=request).suggestion

    assert suggestion.status == SuggestionStatus.PENDING


def test_same_title_but_different_url_as_a_pending_suggestion_is_allowed(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    _pending_suggestion(db_session, country, normalized_url=normalize_url("https://example.gov/other-page"))
    request = _request(country, payload=_payload(official_url="https://example.gov/residency"))

    suggestion = service.create(submitter=HumanSubmitter(user.id), request=request).suggestion

    assert suggestion.status == SuggestionStatus.PENDING


def test_all_conflicts_are_reported_together_documents_first(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    document = _document(db_session, country, slug="other-slug", official_url="https://example.gov/residency")
    pending = _pending_suggestion(db_session, country, normalized_url=normalize_url("https://example.gov/residency"))
    request = _request(
        country,
        payload=_payload(title_i18n={"en": "Something else entirely"}, official_url="https://example.gov/residency"),
    )

    with pytest.raises(DuplicateSuggestionError) as exc_info:
        service.create(submitter=HumanSubmitter(user.id), request=request)

    assert exc_info.value.conflicts == [Conflict("document", document.id), Conflict("suggestion", pending.id)]


def test_two_identical_pending_rows_are_rejected_by_the_database(db_session: Session, country: Jurisdiction) -> None:
    _pending_suggestion(db_session, country, normalized_url="https://example.gov/residency")
    duplicate = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=SuggestionStatus.PENDING,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=country.id,
        payload={"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"},
        normalized_url="https://example.gov/residency",
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_a_non_duplicate_creates_the_suggestion_as_before(
    service: SuggestionService, country: Jurisdiction, user: AppUser
) -> None:
    request = _request(country, payload=_payload(official_url="https://example.gov/brand-new-page"))

    suggestion = service.create(submitter=HumanSubmitter(user.id), request=request).suggestion

    assert suggestion.status == SuggestionStatus.PENDING


def _url_less_request(jurisdiction: Jurisdiction, title: str) -> SuggestionCreate:
    return _request(jurisdiction, payload=NewDocumentPayload(title_i18n={"en": title}))


def test_two_url_less_documents_with_different_slugs_do_not_conflict(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    _document(db_session, country, slug="birth-certificate", official_url=None)
    submitter = HumanSubmitter(user.id)
    first = service.create(submitter=submitter, request=_url_less_request(country, "Residency permit")).suggestion

    second = service.create(submitter=submitter, request=_url_less_request(country, "Passport")).suggestion

    assert (first.status, second.status) == (SuggestionStatus.PENDING, SuggestionStatus.PENDING)
    assert (first.normalized_url, second.normalized_url) == (None, None)


def test_same_slug_still_conflicts_without_a_url(
    service: SuggestionService, db_session: Session, country: Jurisdiction, user: AppUser
) -> None:
    document = _document(db_session, country, slug="residency-permit", official_url=None)

    with pytest.raises(DuplicateSuggestionError) as exc_info:
        service.create(submitter=HumanSubmitter(user.id), request=_url_less_request(country, "Residency Permit"))

    assert exc_info.value.conflicts == [Conflict("document", document.id)]
