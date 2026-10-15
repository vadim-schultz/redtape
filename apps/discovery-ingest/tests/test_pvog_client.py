"""PVOG Suchdienst client pagination tests (chapter 13)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
from discovery_ingest.pvog.client import PvogClient, map_pvog_record

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pvog"
FEDERAL_ARS = "000000000000"
FEDERAL_JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")
BASE = "https://pvog.fitko.net/suchdienst/api"


def _fixture_transport(pages: dict[str, Path]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = pages.get(str(request.url))
        if path is None:
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=json.loads(path.read_text(encoding="utf-8")))

    return httpx.MockTransport(handler)


def test_pvog_client_follows_next_link_in_fixture_pagination() -> None:
    """PvogClient · follows next link in fixture pagination."""
    pages = {
        f"{BASE}/v7/servicedescriptions/{FEDERAL_ARS}": FIXTURE_DIR / "page1.json",
        f"{BASE}/v7/servicedescriptions/{FEDERAL_ARS}?page=2": FIXTURE_DIR / "page2.json",
        f"{BASE}/v7/servicedescriptions/{FEDERAL_ARS}?page=3": FIXTURE_DIR / "page3_empty.json",
    }
    client = PvogClient(BASE, http_client=httpx.Client(transport=_fixture_transport(pages)))

    records = list(client.iter_records(ars=FEDERAL_ARS))

    assert len(records) == 2
    assert records[0]["id"] == "OD-EXAMPLE-001"
    assert records[1]["id"] == "OD-EXAMPLE-002"


def test_pvog_client_respects_max_pages_cap() -> None:
    """PvogClient · respects max_pages cap."""
    pages = {
        f"{BASE}/v7/servicedescriptions/{FEDERAL_ARS}": FIXTURE_DIR / "page1.json",
        f"{BASE}/v7/servicedescriptions/{FEDERAL_ARS}?page=2": FIXTURE_DIR / "page2.json",
        f"{BASE}/v7/servicedescriptions/{FEDERAL_ARS}?page=3": FIXTURE_DIR / "page3_empty.json",
    }
    client = PvogClient(BASE, http_client=httpx.Client(transport=_fixture_transport(pages)))

    records = list(client.iter_records(ars=FEDERAL_ARS, max_pages=1))

    assert len(records) == 1
    assert records[0]["id"] == "OD-EXAMPLE-001"


def test_pvog_client_stops_on_empty_page() -> None:
    """PvogClient · stops on empty page."""
    pages = {
        f"{BASE}/v7/servicedescriptions/{FEDERAL_ARS}": FIXTURE_DIR / "page3_empty.json",
    }
    client = PvogClient(BASE, http_client=httpx.Client(transport=_fixture_transport(pages)))

    records = list(client.iter_records(ars=FEDERAL_ARS))

    assert records == []


def test_pvog_client_maps_fixture_row_to_batch_upsert_dto() -> None:
    """PvogClient · maps fixture row to batch upsert DTO."""
    row = json.loads((FIXTURE_DIR / "page1.json").read_text(encoding="utf-8"))["content"][0]
    item = map_pvog_record(row, jurisdiction_id=FEDERAL_JURISDICTION)

    assert item.source == "pvog"
    assert item.external_id == "pvog:PORTAL-BUND-01:OD-EXAMPLE-001"
    assert item.jurisdiction_id == FEDERAL_JURISDICTION
    assert item.title_i18n == {"de": "Beispiel-Onlinedienst"}
    assert item.description_i18n == {"de": "Kurzbeschreibung aus PVOG"}
    assert item.portal_url == "https://example.bund.de/onlinedienst"
    assert item.raw_payload["lbId"] == "LB-001"
