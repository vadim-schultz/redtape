"""PVOG Suchdienst client v7 tree walk and pagination tests."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest
from discovery_ingest.pvog.client import (
    PvogClient,
    PvogClientError,
    PvogMappingError,
    PvogStash,
    _build_v7_url,
    map_pvog_record,
)
from discovery_ingest.pvog.models import PvogBootstrap, PvogPage, PvogRecord, PvogSourcePath
from discovery_ingest.schemas import CatalogueBatchItem

from crosswalk_fakes import CROSSWALK

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pvog"
FEDERAL_ARS = "000000000000"
FEDERAL_JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")
BASE = "https://pvog.fitko.net/suchdienst/api"


def _map(
    record: PvogRecord,
    *,
    jurisdiction_id: uuid.UUID,
    personal_matter_code: str | None = None,
    personal_matter_path: PvogSourcePath | None = None,
) -> CatalogueBatchItem:
    """Map ``record`` stamped with the served mapping version, as the catalogue run does."""
    stash = PvogStash(CROSSWALK.artifact_version, personal_matter_code, personal_matter_path)
    return map_pvog_record(record, jurisdiction_id=jurisdiction_id, stash=stash)


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

    codes = PvogBootstrap.model_validate(payload).leaf_codes()

    assert codes == ["LEAF_A", "LEAF_B", "LEAF_C"]


def test_personal_matter_codes_from_facades_empty_tree() -> None:
    """Facades tree · empty or missing facades returns no codes."""
    assert PvogBootstrap.model_validate({}).leaf_codes() == []
    assert PvogBootstrap.model_validate({"facades": {}}).leaf_codes() == []


def test_v7_page_extracts_service_descriptions_content() -> None:
    """v7 page parser · reads serviceDescriptions.content."""
    payload = _load_fixture("v7_page_leaf_a.json")

    records, is_last = PvogPage.model_validate(payload).records_and_last

    assert len(records) == 1
    assert records[0].raw["id"] == "SHARED-LB-001"
    assert is_last is True


def test_v7_page_missing_service_descriptions_returns_empty() -> None:
    """v7 page parser · missing wrapper yields no records."""
    records, is_last = PvogPage.model_validate({"content": [{"id": "legacy"}]}).records_and_last

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

    ids = [record.raw["id"] for _code, record in records]
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
    assert records[0][1].raw["id"] == "PAGE-ROW-001"


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

    assert [record.raw["id"] for _code, record in records] == ["PAGE-ROW-001", "PAGE-ROW-002"]


def test_map_pvog_record_live_shape_leika_and_portal_url() -> None:
    """map_pvog_record · LeiKa id and portal URI from live v7 row."""
    row = _load_fixture("live_shape_row.json")
    item = _map(PvogRecord.model_validate(row), jurisdiction_id=FEDERAL_JURISDICTION)

    assert item.source == "pvog"
    assert item.external_id == "pvog:leika:99001040001000"
    assert item.jurisdiction_id == FEDERAL_JURISDICTION
    assert item.title_i18n == {"de": "Live v7 Leistungsname"}
    assert item.description_i18n == {"de": "Kurzer Teaser"}
    assert item.portal_url == "https://service.example.bund.de/online"


def test_map_pvog_record_rejects_row_without_id_and_leika() -> None:
    """map_pvog_record · rejects row without lb id and LeiKa key."""
    with pytest.raises(PvogMappingError, match="external id"):
        _map(PvogRecord.model_validate({"name": "orphan"}), jurisdiction_id=FEDERAL_JURISDICTION)


def test_pvog_client_fetches_full_personal_matter_vocabulary() -> None:
    """PvogClient · fetches the bootstrap page and returns its full leaf vocabulary."""
    pages = {_bootstrap_url(): FIXTURE_DIR / "facades_personal_matters.json"}
    client = PvogClient(BASE, http_client=httpx.Client(transport=_fixture_transport(pages)))

    codes = client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)

    assert codes == ["LEAF_A", "LEAF_B", "LEAF_C"]


def test_map_pvog_record_stashes_personal_matter_code_into_raw_payload() -> None:
    """map_pvog_record · stashes the given Lebenslage code into raw_payload under a reserved key."""
    row = _load_fixture("live_shape_row.json")

    item = _map(PvogRecord.model_validate(row), jurisdiction_id=FEDERAL_JURISDICTION, personal_matter_code="1040300")

    assert item.raw_payload["_personal_matter_code"] == "1040300"
    assert row.get("_personal_matter_code") is None


def test_map_pvog_record_leaves_raw_payload_unchanged_without_a_personal_matter_code() -> None:
    """map_pvog_record · leaves raw_payload unchanged when no code is given."""
    row = _load_fixture("live_shape_row.json")

    item = _map(PvogRecord.model_validate(row), jurisdiction_id=FEDERAL_JURISDICTION)

    assert "_personal_matter_code" not in item.raw_payload


def test_pvog_bootstrap_path_preserves_root_parent_leaf_and_source_version() -> None:
    """PVOG · bootstrap path preserves root, parent, leaf and source version."""
    payload = {
        "sourceVersion": "v7",
        "facades": {
            "personalMatters": [
                {
                    "code": "ROOT",
                    "label": "Root",
                    "children": [
                        {
                            "code": "PARENT",
                            "label": "Parent",
                            "children": [{"code": "LEAF", "label": "Leaf"}],
                        }
                    ],
                }
            ]
        },
    }
    bootstrap = PvogBootstrap.model_validate(payload)

    assert bootstrap.path_for("LEAF") == PvogSourcePath(
        root_code="ROOT",
        root_label="Root",
        parent_code="PARENT",
        parent_label="Parent",
        leaf_code="LEAF",
        leaf_label="Leaf",
        source_version="v7",
    )
    pages = {
        _bootstrap_url(): payload,
        _search_url("LEAF"): {
            "serviceDescriptions": {
                "content": [{"id": "LEAF-ROW", "title": "Leaf service"}],
                "last": True,
            }
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        response = pages.get(str(request.url))
        return httpx.Response(200, json=response) if response is not None else httpx.Response(404)

    client = PvogClient(BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    records = list(client.iter_records(ars=FEDERAL_ARS))
    item = _map(records[0][1], jurisdiction_id=FEDERAL_JURISDICTION, personal_matter_code=records[0][0])

    assert [code for code, _record in records] == ["LEAF"]
    assert item.raw_payload["_pvog_source_path"] == bootstrap.path_for("LEAF").as_raw()


def test_pvog_missing_parent_metadata_does_not_invent_a_product_category() -> None:
    """PVOG · missing parent metadata retains the leaf fact without a category hint."""
    path = PvogSourcePath(
        root_code=None,
        root_label=None,
        parent_code=None,
        parent_label=None,
        leaf_code="1010100",
        leaf_label=None,
        source_version="v7",
    )

    assert CROSSWALK.evidence_for_path(path) is None


def test_map_pvog_record_stamps_the_mapping_version_it_is_given_on_a_stored_path() -> None:
    """map_pvog_record · a stored source path carries the mapping version the caller passes, not a stored constant."""
    row = _load_fixture("v7_page_cli_single.json")["serviceDescriptions"]["content"][0]
    path = PvogSourcePath(
        root_code="1",
        root_label="Lebenslagen für Bürgerinnen und Bürger",
        parent_code="118",
        parent_label="Altersvorsorge und Ruhestand",
        leaf_code="1180100",
        leaf_label="Altersvorsorge",
        source_version="v7",
    )

    stash = PvogStash("category-contract-v2", "1180100", path)
    item = map_pvog_record(PvogRecord.model_validate(row), jurisdiction_id=FEDERAL_JURISDICTION, stash=stash)

    assert item.raw_payload["_pvog_category_mapping_version"] == "category-contract-v2"


def test_pvog_client_maps_fixture_row_to_batch_upsert_dto() -> None:
    """PvogClient · maps v7 CLI fixture row to batch upsert DTO."""
    row = _load_fixture("v7_page_cli_single.json")["serviceDescriptions"]["content"][0]
    item = _map(PvogRecord.model_validate(row), jurisdiction_id=FEDERAL_JURISDICTION)

    assert item.source == "pvog"
    assert item.external_id == "pvog:leika:99001040001000"
    assert item.jurisdiction_id == FEDERAL_JURISDICTION
    assert item.title_i18n == {"de": "Live v7 Leistungsname"}
    assert item.description_i18n == {"de": "Kurzbeschreibung aus PVOG"}
    assert item.portal_url == "https://service.example.bund.de/online"
    assert item.raw_payload["id"] == "LB-LIVE-CLI-001"


def test_pvog_client_raises_its_own_error_on_a_connection_failure() -> None:
    """PvogClient · _fetch_page wraps a transport failure in PvogClientError, chaining the original cause."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = PvogClient(BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(PvogClientError) as caught:
        client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)

    assert isinstance(caught.value.__cause__, httpx.ConnectError)


def test_pvog_client_raises_its_own_error_on_invalid_json() -> None:
    """PvogClient · a body that is not JSON raises PvogClientError, not a bare ValueError."""
    client = PvogClient(
        BASE, http_client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="not json")))
    )

    with pytest.raises(PvogClientError, match="invalid JSON"):
        client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)


def test_pvog_client_raises_its_own_error_on_a_non_object_payload() -> None:
    """PvogClient · a JSON array body raises PvogClientError, not a bare ValueError."""
    client = PvogClient(
        BASE, http_client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])))
    )

    with pytest.raises(PvogClientError, match="expected JSON object"):
        client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)


def test_pvog_client_keeps_the_http_status_message() -> None:
    """PvogClient · a 404 still raises PvogClientError with the same message as before."""
    client = PvogClient(BASE, http_client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))))

    with pytest.raises(PvogClientError, match="PVOG Suchdienst HTTP 404"):
        client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)
