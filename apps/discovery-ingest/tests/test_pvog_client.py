"""PVOG Suchdienst client v7 tree walk and pagination tests."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest
from discovery_ingest.pvog.client import (
    PvogClient,
    PvogMappingError,
    _build_v7_url,
    _parse_v7_page,
    _personal_matter_codes_from_facades,
    map_pvog_record,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pvog"
FEDERAL_ARS = "000000000000"
FEDERAL_JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")
BASE = "https://pvog.fitko.net/suchdienst/api"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _fixture_transport(pages: dict[str, Path]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = pages.get(str(request.url))
        if path is None:
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=json.loads(path.read_text(encoding="utf-8")))

    return httpx.MockTransport(handler)


def _bootstrap_url() -> str:
    return _build_v7_url(
        BASE,
        FEDERAL_ARS,
        personal_matter="Geburt",
        facades=True,
    )


def _search_url(code: str, page: int = 0) -> str:
    return _build_v7_url(
        BASE,
        FEDERAL_ARS,
        personal_matter=code,
        facades=False,
        page=page,
    )


def test_personal_matter_codes_from_facades_leaf_only_sorted() -> None:
    """Facades tree · leaf codes only, sorted."""
    payload = _load_fixture("facades_personal_matters.json")

    codes = _personal_matter_codes_from_facades(payload)

    assert codes == ["LEAF_A", "LEAF_B", "LEAF_C"]


def test_personal_matter_codes_from_facades_empty_tree() -> None:
    """Facades tree · empty or missing facades returns no codes."""
    assert _personal_matter_codes_from_facades({}) == []
    assert _personal_matter_codes_from_facades({"facades": {}}) == []


def test_v7_page_extracts_service_descriptions_content() -> None:
    """v7 page parser · reads serviceDescriptions.content."""
    payload = _load_fixture("v7_page_leaf_a.json")

    records, is_last = _parse_v7_page(payload)

    assert len(records) == 1
    assert records[0]["id"] == "SHARED-LB-001"
    assert is_last is True


def test_v7_page_missing_service_descriptions_returns_empty() -> None:
    """v7 page parser · missing wrapper yields no records."""
    records, is_last = _parse_v7_page({"content": [{"id": "legacy"}]})

    assert records == []
    assert is_last is True


def test_pvog_client_iterates_personal_matter_codes_with_dedupe() -> None:
    """PvogClient · walks leaf codes and dedupes lb id across codes."""
    pages = {
        _bootstrap_url(): FIXTURE_DIR / "facades_personal_matters.json",
        _search_url("LEAF_A"): FIXTURE_DIR / "v7_page_leaf_a.json",
        _search_url("LEAF_B"): FIXTURE_DIR / "v7_page_leaf_b.json",
        _search_url("LEAF_C"): FIXTURE_DIR / "v7_page_leaf_a.json",
    }
    client = PvogClient(BASE, http_client=httpx.Client(transport=_fixture_transport(pages)))

    records = list(client.iter_records(ars=FEDERAL_ARS))

    ids = [row["id"] for row in records]
    assert ids == ["SHARED-LB-001", "UNIQUE-LB-002"]


def test_pvog_client_stops_at_max_pages_budget() -> None:
    """PvogClient · global max_pages counts bootstrap and search GETs."""
    pages = {
        _bootstrap_url(): FIXTURE_DIR / "facades_personal_matters.json",
        _search_url("LEAF_A", 0): FIXTURE_DIR / "v7_page_paged_code.json",
        _search_url("LEAF_A", 1): FIXTURE_DIR / "v7_page_paged_code_page2.json",
    }
    client = PvogClient(BASE, http_client=httpx.Client(transport=_fixture_transport(pages)))

    records = list(client.iter_records(ars=FEDERAL_ARS, max_pages=2))

    assert len(records) == 1
    assert records[0]["id"] == "PAGE-ROW-001"


def test_pvog_client_paginates_until_service_descriptions_last() -> None:
    """PvogClient · advances page while serviceDescriptions.last is false."""
    facades = {
        "facades": {
            "personalMatters": [{"code": "LEAF_PAGED", "label": "Paged leaf"}],
        },
    }
    pages = {
        _bootstrap_url(): None,
        _search_url("LEAF_PAGED", 0): FIXTURE_DIR / "v7_page_paged_code.json",
        _search_url("LEAF_PAGED", 1): FIXTURE_DIR / "v7_page_paged_code_page2.json",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        key = str(request.url)
        if key == _bootstrap_url():
            return httpx.Response(200, json=facades)
        path = pages.get(key)
        if path is None:
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=json.loads(path.read_text(encoding="utf-8")))

    client = PvogClient(BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    records = list(client.iter_records(ars=FEDERAL_ARS))

    assert [row["id"] for row in records] == ["PAGE-ROW-001", "PAGE-ROW-002"]


def test_map_pvog_record_live_shape_leika_and_portal_url() -> None:
    """map_pvog_record · LeiKa id and portal URI from live v7 row."""
    row = _load_fixture("live_shape_row.json")
    item = map_pvog_record(row, jurisdiction_id=FEDERAL_JURISDICTION)

    assert item.source == "pvog"
    assert item.external_id == "pvog:leika:99001040001000"
    assert item.jurisdiction_id == FEDERAL_JURISDICTION
    assert item.title_i18n == {"de": "Live v7 Leistungsname"}
    assert item.description_i18n == {"de": "Kurzer Teaser"}
    assert item.portal_url == "https://service.example.bund.de/online"


def test_map_pvog_record_rejects_row_without_id_and_leika() -> None:
    """map_pvog_record · rejects row without lb id and LeiKa key."""
    with pytest.raises(PvogMappingError, match="external id"):
        map_pvog_record({"name": "orphan"}, jurisdiction_id=FEDERAL_JURISDICTION)


def test_pvog_client_fetches_full_personal_matter_vocabulary() -> None:
    """PvogClient · fetches the bootstrap page and returns its full leaf vocabulary."""
    pages = {_bootstrap_url(): FIXTURE_DIR / "facades_personal_matters.json"}
    client = PvogClient(BASE, http_client=httpx.Client(transport=_fixture_transport(pages)))

    codes = client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)

    assert codes == ["LEAF_A", "LEAF_B", "LEAF_C"]


def test_pvog_client_maps_fixture_row_to_batch_upsert_dto() -> None:
    """PvogClient · maps v7 CLI fixture row to batch upsert DTO."""
    row = _load_fixture("v7_page_cli_single.json")["serviceDescriptions"]["content"][0]
    item = map_pvog_record(row, jurisdiction_id=FEDERAL_JURISDICTION)

    assert item.source == "pvog"
    assert item.external_id == "pvog:leika:99001040001000"
    assert item.jurisdiction_id == FEDERAL_JURISDICTION
    assert item.title_i18n == {"de": "Live v7 Leistungsname"}
    assert item.description_i18n == {"de": "Kurzbeschreibung aus PVOG"}
    assert item.portal_url == "https://service.example.bund.de/online"
    assert item.raw_payload["id"] == "LB-LIVE-CLI-001"
