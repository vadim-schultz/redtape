"""Machine route that serves the tag vocabulary (extraction chapter E1, loop D)."""

from __future__ import annotations

from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session

from test_discovery_machine_api import _issue_key, client  # noqa: F401

TAXONOMY_URL = "/api/v1/discovery/machine/taxonomy"


def test_taxonomy_route_returns_the_vocabulary_in_sort_order(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    seed_taxonomy(db_session)

    response = client.get(TAXONOMY_URL, headers={"X-API-Key": _issue_key(db_session)})

    assert response.status_code == 200
    body = response.json()
    assert (len(body["domains"]), len(body["situations"])) == (13, 18)
    first = body["domains"][0]
    assert set(first) == {"code", "name_i18n", "description_i18n"}
    assert {"de", "en"} <= set(first["name_i18n"])
    assert [t["code"] for t in body["domains"]] == _in_seed_order("domains")
    assert [t["code"] for t in body["situations"]] == _in_seed_order("situations")


def _in_seed_order(axis: str) -> list[str]:
    from scripts.seed_data.taxonomy import DOMAINS, SITUATIONS

    terms = DOMAINS if axis == "domains" else SITUATIONS
    return [t.code for t in sorted(terms, key=lambda t: (t.sort_order, t.code))]


def test_taxonomy_route_requires_the_machine_key(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    seed_taxonomy(db_session)

    assert client.get(TAXONOMY_URL).status_code == 401
    assert client.get(TAXONOMY_URL, headers={"X-API-Key": "rt_wrong"}).status_code == 401
