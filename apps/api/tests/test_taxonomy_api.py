from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.main import create_app
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    # tags={}: this suite only needs the domain/life-situation vocabulary, not
    # the document tags, which reference a document graph this fixture never seeds.
    seed_taxonomy(db_session)
    db_session.flush()
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


def test_domains_are_returned_in_sort_order(client: TestClient[Litestar]) -> None:
    body = client.get("/api/v1/domains").json()

    assert len(body) == 13
    assert body[0]["code"] == "identity-civil-status"
    assert set(body[0]) == {"code", "name", "description", "icon"}


def test_domain_names_resolve_to_the_request_locale(client: TestClient[Litestar]) -> None:
    de = client.get("/api/v1/domains", headers={"Accept-Language": "de"}).json()
    en = client.get("/api/v1/domains", headers={"Accept-Language": "en"}).json()

    assert de[0]["name"] != en[0]["name"]
    assert en[0]["name"] == "Identity & civil status"


def test_domain_names_fall_back_to_de_when_locale_has_no_name(client: TestClient[Litestar]) -> None:
    de = client.get("/api/v1/domains", headers={"Accept-Language": "de"}).json()
    fr = client.get("/api/v1/domains", headers={"Accept-Language": "fr"}).json()

    assert fr == de


def test_life_situations_return_18_with_icon_and_code(client: TestClient[Litestar]) -> None:
    body = client.get("/api/v1/life-situations").json()

    assert len(body) == 18
    assert all(item["code"] and item["icon"] for item in body)


def test_life_situations_each_carry_a_group_code_that_resolves_to_a_real_group(client: TestClient[Litestar]) -> None:
    situations = client.get("/api/v1/life-situations").json()
    group_codes = {g["code"] for g in client.get("/api/v1/life-situation-groups").json()}

    assert all(item["group_code"] in group_codes for item in situations)


def test_life_situation_groups_are_returned_in_sort_order(client: TestClient[Litestar]) -> None:
    body = client.get("/api/v1/life-situation-groups").json()

    assert len(body) == 8
    assert body[0]["code"] == "family-relationships"
    assert set(body[0]) == {"code", "name", "description", "icon"}


def test_categories_return_ordered_localized_roots_and_children(client: TestClient[Litestar]) -> None:
    de = client.get("/api/v1/categories", headers={"Accept-Language": "de"})
    en = client.get("/api/v1/categories", headers={"Accept-Language": "en"})

    assert de.status_code == en.status_code == 200
    assert [root["code"] for root in de.json()] == [
        "family-and-relationships",
        "home-and-housing",
        "work-and-employment",
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
