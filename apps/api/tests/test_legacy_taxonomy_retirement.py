"""Chapter 9 reference gate: retired taxonomy routes and inputs fail explicitly and never widen a query."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.main import create_app
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Category
from app.schema.discovery.candidates import CandidateMentionItem
from app.schema.suggestion.payload import NewDocumentPayload
from litestar import Litestar
from litestar.testing import TestClient
from pydantic import ValidationError
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session

RETIRED_ROUTES = (
    "/api/v1/domains",
    "/api/v1/life-situations",
    "/api/v1/life-situation-groups",
    "/api/v1/matrix",
)
RETIRED_DOCUMENT_PARAMS = (
    "domain",
    "filter[domain]",
    "group",
    "filter[group]",
    "situation",
    "filter[situation]",
)
RETIRED_CANDIDATE_FILTERS = ("filter[domain]", "filter[group]", "filter[situation]")
DOCUMENTS_URL = "/api/v1/documents"
CANDIDATES_URL = "/api/v1/candidates"


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    seed_canonical_taxonomy(db_session)
    db_session.flush()
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def country_id(db_session: Session) -> uuid.UUID:
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        code="ZZ",
        administrative_roles=["COUNTRY"],
        name_i18n={"de": "Testland"},
        multiple_postal_codes=False,
        last_updated=datetime.now(UTC),
    )
    db_session.add(country)
    db_session.flush()
    return country.id


def _category_document(session: Session, jurisdiction_id: uuid.UUID, slug: str, category_code: str) -> None:
    category = session.scalars(select(Category).where(Category.code == category_code)).one()
    session.add(
        Document(
            jurisdiction_id=jurisdiction_id,
            slug=slug,
            title_i18n={"de": slug},
            description_i18n={"de": ""},
            categories=[category],
        )
    )


@pytest.mark.parametrize("route", RETIRED_ROUTES)
def test_retired_taxonomy_route_is_absent(client: TestClient[Litestar], route: str) -> None:
    assert client.get(route).status_code == 404


@pytest.mark.parametrize("param", RETIRED_DOCUMENT_PARAMS)
def test_retired_document_filter_is_rejected_with_a_retirement_diagnostic(
    client: TestClient[Litestar], country_id: uuid.UUID, param: str
) -> None:
    response = client.get(DOCUMENTS_URL, params={"jurisdiction_id": str(country_id), param: "housing"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "retired" in detail.lower()
    assert param in detail


def test_category_only_browse_returns_documents_linked_to_the_category(
    client: TestClient[Litestar], db_session: Session, country_id: uuid.UUID
) -> None:
    _category_document(db_session, country_id, "linked-to-housing", "home-and-housing")
    _category_document(db_session, country_id, "linked-to-moving", "moving-house")
    db_session.flush()

    response = client.get(DOCUMENTS_URL, params={"jurisdiction_id": str(country_id), "category": "home-and-housing"})

    assert response.status_code == 200
    body = response.json()
    assert [item["slug"] for item in body["items"]] == ["linked-to-housing", "linked-to-moving"]
    assert body["total"] == 2
    assert "available_leaf_codes" not in body


@pytest.mark.parametrize("param", RETIRED_CANDIDATE_FILTERS)
def test_retired_candidate_filter_is_rejected_with_a_retirement_diagnostic(
    client: TestClient[Litestar], param: str
) -> None:
    response = client.get(CANDIDATES_URL, params={param: "housing"})

    assert response.status_code == 422
    assert "retired" in response.text.lower()


def _mention_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "catalogue_service_id": str(uuid.uuid4()),
        "title_i18n": {"de": "Antrag"},
        "role": "required",
        "excerpt": "Ein Antrag ist erforderlich.",
        "source_field": "documents",
        "extractor": "llm",
        "extractor_version": "1",
    }
    payload.update(changes)
    return payload


def test_mention_payload_rejects_retired_axis_fields_with_a_retirement_diagnostic() -> None:
    with pytest.raises(ValidationError, match="retired"):
        CandidateMentionItem.model_validate(_mention_payload(domain_codes=["housing"]))


def test_mention_payload_rejects_retired_situation_fields_with_a_retirement_diagnostic() -> None:
    with pytest.raises(ValidationError, match="retired"):
        CandidateMentionItem.model_validate(_mention_payload(situation_codes=["moving-house"]))


def test_suggestion_payload_rejects_retired_axis_fields_with_a_retirement_diagnostic() -> None:
    with pytest.raises(ValidationError, match="retired"):
        NewDocumentPayload.model_validate({"title_i18n": {"de": "Antrag"}, "domain_codes": ["housing"]})


def test_suggestion_payload_accepts_category_codes_without_retirement_error() -> None:
    payload = NewDocumentPayload.model_validate({"title_i18n": {"de": "Antrag"}, "category_codes": ["moving-house"]})

    assert payload.category_codes == ["moving-house"]
