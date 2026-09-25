from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.main import create_app
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient[Litestar]]:
    seed_taxonomy(db_session)
    db_session.flush()
    app = create_app()
    app.dependencies["session"] = Provide(lambda: db_session, use_cache=False, sync_to_thread=False)
    with TestClient(app) as test_client:
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
