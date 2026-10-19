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
    assert item.external_id == "govdata:leika:12345678901234"
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


def test_govdata_client_maps_leika_name_to_title() -> None:
    """GovDataClient · maps OpenPvogDto leika_name to title_i18n."""
    live_fixture = Path(__file__).parent / "fixtures" / "govdata" / "open_pvog_live_shape.json"
    client = GovDataOzgClient.from_json_file(live_fixture)
    item = map_govdata_record(client.records[0], federal_jurisdiction_id=FEDERAL_JURISDICTION)

    assert item.title_i18n == {
        "de": "Erlaubnis für die Teilnahme am Betäubungsmittelverkehr beantragen",
    }
    assert item.description_i18n == {
        "de": "Erlaubnis zum Verkehr mit Betäubungsmitteln Erteilung",
    }
    assert item.external_id == "govdata:leika:99003007001000"


def test_govdata_client_rejects_row_without_title() -> None:
    """GovDataClient · rejects row with no title fields."""
    row = {"leika_key": "99001040001000", "ars": "000000000000", "ozgid": 1}

    with pytest.raises(GovDataMappingError, match="no title"):
        map_govdata_record(row, federal_jurisdiction_id=FEDERAL_JURISDICTION)


def test_govdata_client_uses_leika_key_when_ozgid_shared() -> None:
    """GovDataClient · distinct external_id per leika_key when ozgid repeats."""
    shared_ozgid = 10641
    row_a = {
        "leika_key": "99003007001000",
        "leika_name": "Service A",
        "ars": "000000000000",
        "ozgid": shared_ozgid,
    }
    row_b = {
        "leika_key": "99003007011000",
        "leika_name": "Service B",
        "ars": "000000000000",
        "ozgid": shared_ozgid,
    }
    id_a = map_govdata_record(row_a, federal_jurisdiction_id=FEDERAL_JURISDICTION).external_id
    id_b = map_govdata_record(row_b, federal_jurisdiction_id=FEDERAL_JURISDICTION).external_id

    assert id_a == "govdata:leika:99003007001000"
    assert id_b == "govdata:leika:99003007011000"
    assert id_a != id_b
