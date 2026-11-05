"""Machine route that serves the tag vocabulary (extraction chapter E1, loop D)."""

from __future__ import annotations

from app.schema.suggestion.payload import ACTIVE_CATEGORY_CODES
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session

from test_discovery_machine_api import _issue_key, client  # noqa: F401

TAXONOMY_URL = "/api/v1/discovery/machine/taxonomy"


def test_taxonomy_route_returns_the_vocabulary_in_sort_order(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    seed_canonical_taxonomy(db_session)

    response = client.get(TAXONOMY_URL, headers={"X-API-Key": _issue_key(db_session)})

    assert response.status_code == 200
    body = response.json()
    assert len(body["categories"]) == 34
    first = body["categories"][0]
    assert set(first) == {"code", "parent_code", "name_i18n", "description_i18n", "icon", "source_parent_codes"}
    assert {"de", "en"} <= set(first["name_i18n"])
    assert [t["code"] for t in body["categories"]] == _in_seed_order()
    assert all(not term["code"].isdigit() for term in body["categories"])


def _in_seed_order() -> list[str]:
    from scripts.seed_data.taxonomy import CATEGORY_INVENTORY

    return [term.code for term in CATEGORY_INVENTORY]


def test_taxonomy_route_requires_the_machine_key(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    seed_canonical_taxonomy(db_session)

    assert client.get(TAXONOMY_URL).status_code == 401
    assert client.get(TAXONOMY_URL, headers={"X-API-Key": "rt_wrong"}).status_code == 401


def test_machine_taxonomy_excludes_source_only_pvog_leaf_codes(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:  # noqa: F811
    seed_canonical_taxonomy(db_session)

    response = client.get(TAXONOMY_URL, headers={"X-API-Key": _issue_key(db_session)})

    assert response.status_code == 200
    assert all(not category["code"].isdigit() for category in response.json()["categories"])


def test_machine_vocabulary_is_the_set_the_suggestion_payload_accepts(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    seed_canonical_taxonomy(db_session)

    response = client.get(TAXONOMY_URL, headers={"X-API-Key": _issue_key(db_session)})

    machine_codes = {category["code"] for category in response.json()["categories"]}
    assert machine_codes == set(ACTIVE_CATEGORY_CODES)
