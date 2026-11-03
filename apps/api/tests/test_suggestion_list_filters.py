"""Characterisation of the suggestion list filters: each axis alone, combined, counts and ordering."""

from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.filters import SuggestionFilters
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import SuggestionService
from app.features.suggestions.submitters import CrawlerSubmitter, HumanSubmitter, Submitter
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.api_key import ApiKey
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.user import AppUser
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload
from sqlalchemy.orm import Session


@pytest.fixture
def country_a(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "A"}, code=f"A{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def country_b(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "B"}, code=f"B{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


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
def service(db_session: Session) -> SuggestionService:
    events = EventLogService(EventLogRepository(db_session))
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    documents = DocumentService(DocumentRepository(db_session), taxonomy)
    return SuggestionService(SuggestionRepository(db_session), documents, taxonomy, events)


def _submit(
    service: SuggestionService, submitter: Submitter, jurisdiction: Jurisdiction, *, source_url: str | None = None
) -> uuid.UUID:
    payload = NewDocumentPayload(title_i18n={"en": f"Doc {uuid.uuid4().hex}"}, official_url=None)
    request = SuggestionCreate(payload=payload, jurisdiction_id=jurisdiction.id, source_url=source_url)
    return service.create(submitter=submitter, request=request).suggestion.id


@pytest.fixture
def seeded(
    service: SuggestionService, country_a: Jurisdiction, country_b: Jurisdiction, user: AppUser, api_key: ApiKey
) -> dict[str, uuid.UUID]:
    """Three suggestions: a pending human in A, a pending crawler in A, and a rejected human in B."""
    human_a = _submit(service, HumanSubmitter(user.id), country_a)
    crawler_a = _submit(service, CrawlerSubmitter(api_key.id), country_a, source_url="https://example.gov/found-here")
    human_b = _submit(service, HumanSubmitter(user.id), country_b)
    service.transition_to(human_b, SuggestionStatus.REJECTED, actor=None)
    return {"human_a": human_a, "crawler_a": crawler_a, "human_b": human_b}


def _ids(service: SuggestionService, filters: SuggestionFilters) -> set[uuid.UUID]:
    result = service.list_suggestions(filters=filters, offset=0, limit=500)
    return {item.id for item in result.items}


def test_list_filters_by_status(service: SuggestionService, seeded: dict[str, uuid.UUID]) -> None:
    pending = _ids(service, SuggestionFilters(status=(SuggestionStatus.PENDING,)))
    rejected = _ids(service, SuggestionFilters(status=(SuggestionStatus.REJECTED,)))

    assert {seeded["human_a"], seeded["crawler_a"]} <= pending
    assert seeded["human_b"] not in pending
    assert seeded["human_b"] in rejected
    assert not ({seeded["human_a"], seeded["crawler_a"]} & rejected)


def test_list_filters_by_kind(service: SuggestionService, seeded: dict[str, uuid.UUID]) -> None:
    documents = _ids(service, SuggestionFilters(kind=SuggestionKind.NEW_DOCUMENT))
    requirements = _ids(service, SuggestionFilters(kind=SuggestionKind.NEW_REQUIREMENT))

    assert set(seeded.values()) <= documents
    assert not (set(seeded.values()) & requirements)


def test_list_filters_by_source_type(service: SuggestionService, seeded: dict[str, uuid.UUID]) -> None:
    human = _ids(service, SuggestionFilters(source_type=SuggestionSource.HUMAN))
    crawler = _ids(service, SuggestionFilters(source_type=SuggestionSource.CRAWLER))

    assert {seeded["human_a"], seeded["human_b"]} <= human
    assert seeded["crawler_a"] not in human
    assert seeded["crawler_a"] in crawler
    assert not ({seeded["human_a"], seeded["human_b"]} & crawler)


def test_list_filters_by_jurisdiction(
    service: SuggestionService, seeded: dict[str, uuid.UUID], country_a: Jurisdiction, country_b: Jurisdiction
) -> None:
    in_a = _ids(service, SuggestionFilters(jurisdiction_id=country_a.id))
    in_b = _ids(service, SuggestionFilters(jurisdiction_id=country_b.id))

    assert in_a == {seeded["human_a"], seeded["crawler_a"]}
    assert in_b == {seeded["human_b"]}


def test_list_filters_combined_narrow_to_the_intersection(
    service: SuggestionService, seeded: dict[str, uuid.UUID], country_a: Jurisdiction
) -> None:
    combined = SuggestionFilters(
        status=(SuggestionStatus.PENDING,),
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=country_a.id,
        kind=SuggestionKind.NEW_DOCUMENT,
    )

    assert _ids(service, combined) == {seeded["human_a"]}


def test_empty_filters_return_everything_newest_first(service: SuggestionService, seeded: dict[str, uuid.UUID]) -> None:
    result = service.list_suggestions(filters=SuggestionFilters(), offset=0, limit=500)

    assert set(seeded.values()) <= {item.id for item in result.items}
    keys = [(item.created_at, item.id) for item in result.items]
    assert keys == sorted(keys, reverse=True)


def test_count_matches_list_total_under_filters(
    service: SuggestionService, seeded: dict[str, uuid.UUID], country_a: Jurisdiction
) -> None:
    filters = SuggestionFilters(source_type=SuggestionSource.HUMAN, jurisdiction_id=country_a.id)

    result = service.list_suggestions(filters=filters, offset=0, limit=500)

    assert result.total == len(result.items) == 1


def test_filter_with_no_match_returns_empty_page_and_zero_total(
    service: SuggestionService, seeded: dict[str, uuid.UUID], country_b: Jurisdiction
) -> None:
    filters = SuggestionFilters(status=(SuggestionStatus.APPROVED,), jurisdiction_id=country_b.id)

    result = service.list_suggestions(filters=filters, offset=0, limit=10)

    assert result.items == []
    assert result.total == 0
