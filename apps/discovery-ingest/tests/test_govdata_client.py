"""GovData OZG client mapping tests (chapter 12)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from discovery_ingest.govdata.client import GovDataMappingError, GovDataOzgClient, map_govdata_record

FIXTURE = Path(__file__).parent / "fixtures" / "govdata" / "ozg_page.json"
FEDERAL_JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")


def test_govdata_client_maps_fixture_row_to_batch_upsert_dto() -> None:
    """GovDataClient · maps fixture row to batch upsert DTO."""
    client = GovDataOzgClient.from_json_file(FIXTURE)
    row = client.records[0]
    item = map_govdata_record(row, federal_jurisdiction_id=FEDERAL_JURISDICTION)

    assert item.source == "govdata"
    assert item.external_id == "govdata:ozg:OZ-EXAMPLE-001"
    assert item.jurisdiction_id == FEDERAL_JURISDICTION
    assert item.title_i18n == {"de": "Beispiel-Leistung"}
    assert item.description_i18n == {"de": "Kurztext"}
    assert item.portal_url == "https://example.bund.de/leistung"
    assert item.raw_payload["ozgid"] == "OZ-EXAMPLE-001"
    assert item.raw_payload["leika_key"] == "12345678901234"


def test_govdata_client_rejects_row_without_external_id() -> None:
    """GovDataClient · rejects row without external id."""
    client = GovDataOzgClient.from_json_file(FIXTURE)
    row = client.records[1]

    with pytest.raises(GovDataMappingError, match="external id"):
        map_govdata_record(row, federal_jurisdiction_id=FEDERAL_JURISDICTION)
