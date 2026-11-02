from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import (
    SubmitterRef,
    SuggestionService,
    UnknownJurisdictionError,
    UnknownTaxonomyCodeError,
)
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.api_key import ApiKey
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import SuggestionSource, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.taxonomy import Domain, LifeSituation
from app.models.user import AppUser
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload
from app.url_normalization import normalize_url
from pydantic import ValidationError
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy import select
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
def municipality(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.MUNICIPALITY, name_i18n={"en": "Testville"}, code=f"M{uuid.uuid4().hex[:8]}"
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
def api_key(db_session: Session) -> ApiKey:
    row = ApiKey(name="crawler", key_hash=uuid.uuid4().hex, key_prefix=uuid.uuid4().hex[:8])
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def domain_code(db_session: Session) -> str:
    # tags={}: this suite only resolves codes, not documents.
    seed_taxonomy(db_session)
    db_session.flush()
    return db_session.scalars(select(Domain.code)).first()


@pytest.fixture
def situation_code(db_session: Session, domain_code: str) -> str:
    return db_session.scalars(select(LifeSituation.code)).first()


@pytest.fixture
def event_log_service(db_session: Session) -> EventLogService:
    return EventLogService(EventLogRepository(db_session))


@pytest.fixture
def service(db_session: Session, event_log_service: EventLogService) -> SuggestionService:
    documents = DocumentService(DocumentRepository(db_session), TaxonomyService(TaxonomyRepository(db_session)))
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    return SuggestionService(SuggestionRepository(db_session), documents, taxonomy, event_log_service)


def _payload(**overrides: object) -> NewDocumentPayload:
    defaults: dict[str, object] = {
        "title_i18n": {"en": "Residency permit"},
        "official_url": "https://example.gov/residency",
    }
    defaults.update(overrides)
    return NewDocumentPayload(**defaults)


def _request(
    *, jurisdiction: Jurisdiction | None = None, municipality_code: str | None = None, **overrides: object
) -> SuggestionCreate:
    payload = overrides.pop("payload", _payload())
    data: dict[str, object] = {"payload": payload}
    if municipality_code is not None:
        data["municipality_code"] = municipality_code
    else:
        data["jurisdiction_id"] = jurisdiction.id if jurisdiction is not None else uuid.uuid4()
    data.update(overrides)
    return SuggestionCreate(**data)


def test_stores_a_pending_human_suggestion_for_a_user(
    service: SuggestionService, country: Jurisdiction, user: AppUser
) -> None:
    suggestion = service.create(
        submitter=SubmitterRef("user", user.id), request=_request(jurisdiction=country)
    ).suggestion

    assert suggestion.status == SuggestionStatus.PENDING
    assert suggestion.source_type == SuggestionSource.HUMAN
    assert suggestion.submitted_by_user_id == user.id
    assert suggestion.submitted_by_api_key_id is None


def test_stores_a_pending_crawler_suggestion_for_an_api_key(
    service: SuggestionService, country: Jurisdiction, api_key: ApiKey
) -> None:
    request = _request(jurisdiction=country, source_url="https://example.gov/found-here")

    suggestion = service.create(submitter=SubmitterRef("crawler", api_key.id), request=request).suggestion

    assert suggestion.status == SuggestionStatus.PENDING
    assert suggestion.source_type == SuggestionSource.CRAWLER
    assert suggestion.submitted_by_api_key_id == api_key.id


def test_create_logs_a_submitted_event_for_a_human_submitter(
    service: SuggestionService, event_log_service: EventLogService, country: Jurisdiction, user: AppUser
) -> None:
    suggestion = service.create(
        submitter=SubmitterRef("user", user.id), request=_request(jurisdiction=country)
    ).suggestion

    events = event_log_service.list_for(suggestion.id)
    submitted = [e for e in events if e.event_type == EventType.SUBMITTED]
    assert len(submitted) == 1
    assert submitted[0].actor_user_id == user.id
    assert submitted[0].actor_api_key_id is None


def test_create_logs_a_submitted_event_for_a_crawler_submitter(
    service: SuggestionService, event_log_service: EventLogService, country: Jurisdiction, api_key: ApiKey
) -> None:
    request = _request(jurisdiction=country, source_url="https://example.gov/found-here")

    suggestion = service.create(submitter=SubmitterRef("crawler", api_key.id), request=request).suggestion

    submitted = [e for e in event_log_service.list_for(suggestion.id) if e.event_type == EventType.SUBMITTED]
    assert len(submitted) == 1
    assert submitted[0].actor_api_key_id == api_key.id
    assert submitted[0].actor_user_id is None
    assert suggestion.submitted_by_user_id is None


def test_derives_normalized_url_from_official_url(
    service: SuggestionService, country: Jurisdiction, user: AppUser
) -> None:
    official_url = "https://Example.gov/residency/?utm_source=x&b=2&a=1"
    request = _request(jurisdiction=country, payload=_payload(official_url=official_url))

    suggestion = service.create(submitter=SubmitterRef("user", user.id), request=request).suggestion

    assert suggestion.normalized_url == normalize_url(official_url)


def test_resolves_municipality_code_to_the_jurisdiction_id(
    service: SuggestionService, municipality: Jurisdiction, user: AppUser
) -> None:
    request = _request(municipality_code=municipality.code)

    suggestion = service.create(submitter=SubmitterRef("user", user.id), request=request).suggestion

    assert suggestion.jurisdiction_id == municipality.id


def test_rejects_an_unknown_jurisdiction_id(service: SuggestionService, user: AppUser) -> None:
    request = _request(jurisdiction=None)

    with pytest.raises(UnknownJurisdictionError):
        service.create(submitter=SubmitterRef("user", user.id), request=request)


def test_rejects_an_unknown_municipality_code(service: SuggestionService, user: AppUser) -> None:
    request = _request(municipality_code="does-not-exist")

    with pytest.raises(UnknownJurisdictionError):
        service.create(submitter=SubmitterRef("user", user.id), request=request)


def test_rejects_an_unknown_domain_code(service: SuggestionService, country: Jurisdiction, user: AppUser) -> None:
    request = _request(jurisdiction=country, payload=_payload(domain_codes=["no-such-domain"]))

    with pytest.raises(UnknownTaxonomyCodeError):
        service.create(submitter=SubmitterRef("user", user.id), request=request)


def test_rejects_an_unknown_situation_code(service: SuggestionService, country: Jurisdiction, user: AppUser) -> None:
    request = _request(jurisdiction=country, payload=_payload(situation_codes=["no-such-situation"]))

    with pytest.raises(UnknownTaxonomyCodeError):
        service.create(submitter=SubmitterRef("user", user.id), request=request)


def test_accepts_known_domain_and_situation_codes(
    service: SuggestionService,
    country: Jurisdiction,
    user: AppUser,
    domain_code: str,
    situation_code: str,
) -> None:
    request = _request(
        jurisdiction=country,
        payload=_payload(domain_codes=[domain_code], situation_codes=[situation_code]),
    )

    suggestion = service.create(submitter=SubmitterRef("user", user.id), request=request).suggestion

    assert suggestion.status == SuggestionStatus.PENDING


def test_client_supplied_status_and_source_type_are_rejected_by_the_schema(country: Jurisdiction) -> None:
    with pytest.raises(ValidationError):
        SuggestionCreate.model_validate(
            {
                "payload": _payload().model_dump(mode="json"),
                "jurisdiction_id": str(country.id),
                "status": "approved",
                "source_type": "crawler",
            }
        )


def test_get_returns_none_for_an_unknown_id(service: SuggestionService) -> None:
    assert service.get(uuid.uuid4()) is None
