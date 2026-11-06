"""Machine route that serves the tag vocabulary (extraction chapter E1, loop D)."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.schema.suggestion.payload import ACTIVE_CATEGORY_CODES
from app.shared.taxonomy import contract_loader
from app.shared.taxonomy.contract_loader import load_contract
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


def test_machine_vocabulary_carries_the_pvog_crosswalk_with_its_source_and_artifact_versions(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """machine vocabulary · the response carries the PVOG leaf crosswalk and its versions from the artifact."""
    seed_canonical_taxonomy(db_session)
    contract = load_contract()

    response = client.get(TAXONOMY_URL, headers={"X-API-Key": _issue_key(db_session)})

    crosswalk = response.json()["crosswalk"]
    assert crosswalk["artifact_version"] == contract.artifact_version == "category-contract-v1"
    assert crosswalk["pvog_source_version"] == contract.pvog_source_version == "v7"
    assert len(crosswalk["pvog_leaf_mappings"]) == len(contract.pvog_leaf_mappings)
    assert len(crosswalk["legacy_crosswalk"]) == len(contract.legacy_crosswalk)
    retirement = next(item for item in crosswalk["pvog_leaf_mappings"] if item["leaf_code"] == "1180100")
    assert retirement["category_codes"] == ["retirement"]
    assert retirement["confidence"] == 0.95
    assert retirement["state"] == "mapped"


def test_machine_vocabulary_serves_no_partial_response_when_the_contract_is_unusable(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """machine vocabulary · an unusable contract fails the request; no vocabulary without its crosswalk."""
    seed_canonical_taxonomy(db_session)
    broken = tmp_path / "category_contract_v1.json"
    broken.write_bytes(b'{"artifact_version": "v1"}')
    monkeypatch.setattr(contract_loader, "ARTIFACT_PATH", broken)
    contract_loader.load_contract.cache_clear()
    try:
        response = client.get(TAXONOMY_URL, headers={"X-API-Key": _issue_key(db_session)})
    finally:
        contract_loader.load_contract.cache_clear()

    assert response.status_code == 500
    assert "categories" not in response.text
    assert "crosswalk" not in response.text
