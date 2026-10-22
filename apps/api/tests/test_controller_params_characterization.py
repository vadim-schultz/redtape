"""Characterization: paging, locale and 4xx behaviour of the documents and locations list endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.main import create_app
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

DOCUMENTS = "/api/v1/documents"
COUNTRIES = "/api/v1/countries"


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        code="ZZ",
        administrative_roles=["COUNTRY"],
        name_i18n={"de": "Testland", "en": "Testcountry"},
        multiple_postal_codes=False,
        last_updated=datetime.now(UTC),
    )
    db_session.add(country)
    db_session.flush()
    for slug in ("a", "b", "c"):
        db_session.add(
            Document(
                slug=slug,
                jurisdiction_id=country.id,
                title_i18n={"de": f"T-{slug}"},
                official_url=f"https://example.gov/{slug}",
            )
        )
    db_session.flush()
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


def test_documents_page_reports_offset_limit_and_total(client: TestClient[Litestar]) -> None:
    body = client.get(DOCUMENTS, params={"offset": 1, "limit": 1}).json()

    assert (body["offset"], body["limit"], body["total"], len(body["items"])) == (1, 1, 3, 1)


def test_documents_page_defaults_to_offset_0_limit_20(client: TestClient[Litestar]) -> None:
    body = client.get(DOCUMENTS).json()

    assert (body["offset"], body["limit"]) == (0, 20)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_documents_reject_invalid_paging_with_400(client: TestClient[Litestar], params: dict[str, int]) -> None:
    assert client.get(DOCUMENTS, params=params).status_code == 400


def test_countries_resolve_name_to_the_request_locale(client: TestClient[Litestar]) -> None:
    de = client.get(COUNTRIES, headers={"Accept-Language": "de"}).json()["items"]
    en = client.get(COUNTRIES, params={"locale": "en"}).json()["items"]

    assert (de[0]["name"], en[0]["name"]) == ("Testland", "Testcountry")


def test_unsupported_locale_falls_back_to_de(client: TestClient[Litestar]) -> None:
    body = client.get(COUNTRIES, params={"locale": "xx"}).json()["items"]

    assert body[0]["name"] == "Testland"
