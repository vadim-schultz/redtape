from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.main import create_app
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Category
from httpx import Response
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session

URL = "/api/v1/documents"


def _document(
    session: Session, jurisdiction_id: uuid.UUID, slug: str, category_codes: tuple[str, ...] = ()
) -> Document:
    categories = list(session.scalars(select(Category).where(Category.code.in_(category_codes))).all())
    document = Document(
        jurisdiction_id=jurisdiction_id,
        slug=slug,
        title_i18n={"de": slug},
        description_i18n={"de": ""},
        categories=categories,
    )
    session.add(document)
    return document


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    """Return a document client with canonical category-linked documents."""
    seed_canonical_taxonomy(db_session)
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        code="XX",
        administrative_roles=["COUNTRY"],
        name_i18n={"de": "Testland"},
        multiple_postal_codes=False,
        last_updated=datetime.now(UTC),
    )
    db_session.add(country)
    db_session.flush()
    _document(db_session, country.id, "a-root", ("home-and-housing",))
    _document(db_session, country.id, "b-child", ("moving-house",))
    _document(db_session, country.id, "c-other", ("identity-and-documents",))
    _document(db_session, country.id, "d-untagged")
    db_session.flush()
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        test_client.jurisdiction_id = str(country.id)  # type: ignore[attr-defined]
        yield test_client


def _get(client: TestClient[Litestar], params: dict[str, str] | list[tuple[str, str]]) -> Response:
    """List documents scoped to the test jurisdiction."""
    scope = [("jurisdiction_id", client.jurisdiction_id)]  # type: ignore[attr-defined]
    pairs = list(params.items()) if isinstance(params, dict) else params
    return client.get(URL, params=scope + pairs)


def _slugs(response: Response) -> list[str]:
    return [item["slug"] for item in response.json()["items"]]


def test_category_root_returns_direct_and_descendant_documents(client: TestClient[Litestar]) -> None:
    assert _slugs(_get(client, {"category": "home-and-housing"})) == ["a-root", "b-child"]


def test_repeated_category_filters_are_ored(client: TestClient[Litestar]) -> None:
    assert _slugs(_get(client, [("category", "home-and-housing"), ("category", "identity-and-documents")])) == [
        "a-root",
        "b-child",
        "c-other",
    ]


def test_total_reflects_category_filter_and_pagination(client: TestClient[Litestar]) -> None:
    body = _get(client, {"category": "home-and-housing", "limit": "1"}).json()

    assert body["total"] == 2
    assert len(body["items"]) == 1


def test_unknown_category_code_returns_422(client: TestClient[Litestar]) -> None:
    response = _get(client, {"category": "no-such-category"})

    assert response.status_code == 422
    assert "Unknown category code" in response.json()["detail"]


@pytest.mark.parametrize(
    "param", ("domain", "group", "situation", "filter[domain]", "filter[group]", "filter[situation]")
)
def test_retired_category_inputs_are_rejected(client: TestClient[Litestar], param: str) -> None:
    response = _get(client, {param: "housing"})

    assert response.status_code == 422
    assert "retired" in response.json()["detail"].lower()
    assert param in response.json()["detail"]


def test_no_params_returns_the_unfiltered_list(client: TestClient[Litestar]) -> None:
    body = _get(client, {}).json()

    assert body["total"] == 4
    assert len(body["items"]) == 4


def _detail(client: TestClient[Litestar], slug: str, locale: str = "en") -> dict:
    doc_id = next(i["id"] for i in _get(client, {"limit": "100"}).json()["items"] if i["slug"] == slug)
    return client.get(f"{URL}/{doc_id}", headers={"Accept-Language": locale}).json()


def test_detail_includes_canonical_category_tags(client: TestClient[Litestar]) -> None:
    body = _detail(client, "a-root")

    assert [tag["code"] for tag in body["categories"]] == ["home-and-housing"]
    assert set(body["categories"][0]) == {"code", "name", "confidence"}


def test_detail_document_without_tags_returns_empty_categories(client: TestClient[Litestar]) -> None:
    body = _detail(client, "d-untagged")

    assert body["categories"] == []
