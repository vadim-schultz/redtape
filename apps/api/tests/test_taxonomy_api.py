from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.main import create_app
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    """Return an API client with the canonical category inventory seeded."""
    seed_canonical_taxonomy(db_session)
    db_session.flush()
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


def test_categories_return_ordered_localized_roots_and_children(client: TestClient[Litestar]) -> None:
    de = client.get("/api/v1/categories", headers={"Accept-Language": "de"})
    en = client.get("/api/v1/categories", headers={"Accept-Language": "en"})

    assert de.status_code == en.status_code == 200
    assert [root["code"] for root in de.json()] == [
        "family-and-relationships",
        "home-and-housing",
        "work-and-employment",
        "education-and-training",
        "mobility-and-vehicles",
        "health-and-care",
        "residence-and-migration",
        "retirement-and-old-age",
        "taxes-and-finance",
        "identity-and-documents",
        "social-benefits",
        "law-and-justice",
    ]
    first = de.json()[0]
    assert first["parent_code"] is None
    assert first["icon"] == "users"
    assert [child["code"] for child in first["children"]] == [
        "birth-and-parenthood",
        "marriage-and-partnership",
        "separation-and-divorce",
        "death-and-estate",
    ]
    assert first["children"][0]["parent_code"] == first["code"]
    assert first["name"] != en.json()[0]["name"]
    assert en.json()[0]["name"] == "Family & relationships"


def test_categories_fall_back_to_german_when_requested_locale_is_missing(
    client: TestClient[Litestar],
) -> None:
    de = client.get("/api/v1/categories", headers={"Accept-Language": "de"}).json()
    fr = client.get("/api/v1/categories", headers={"Accept-Language": "fr"}).json()

    assert fr == de


def test_categories_exclude_an_inactive_parent_and_its_children(
    client: TestClient[Litestar], db_session: Session
) -> None:
    from app.models.taxonomy import Category
    from sqlalchemy import update

    db_session.execute(update(Category).where(Category.code == "family-and-relationships").values(is_active=False))
    db_session.flush()

    body = client.get("/api/v1/categories").json()

    assert "family-and-relationships" not in {root["code"] for root in body}


@pytest.mark.parametrize(
    "route",
    (
        "/api/v1/domains",
        "/api/v1/life-situations",
        "/api/v1/life-situation-groups",
        "/api/v1/matrix",
    ),
)
def test_retired_taxonomy_routes_are_absent(client: TestClient[Litestar], route: str) -> None:
    assert client.get(route).status_code == 404
