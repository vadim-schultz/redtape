"""Characterisation of the crawl, enrich and LLM-JSON payload handling.

These tests pin the behaviour the typed models must keep: golden mapper output, ladder order, leniency,
page parsing, the page budget, the LLM JSON schema helpers and the handler table. They run against the
current dict-based code first and stay green through the type changes.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.enrich import (
    fim_steckbrief_claim_requests,
    fim_steckbrief_entity_request,
)
from discovery_ingest.extract.llm.payloads import chat_body, run_body
from discovery_ingest.extract.llm.schema import build_json_schema
from discovery_ingest.extract.llm.schema_prep import prepare_schema
from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.fim.models import Stammtext, Steckbrief
from discovery_ingest.govdata.ckan import GovDataCkanClient, GovDataCkanError
from discovery_ingest.govdata.client import GovDataMappingError, GovDataOzgClient, map_govdata_record
from discovery_ingest.govdata.models import GovDataRow
from discovery_ingest.leika.client import LeikaClientError, LeikaStammtextClient
from discovery_ingest.pvog.client import PvogClient, PvogClientError, PvogMappingError, map_pvog_record
from discovery_ingest.pvog.models import PvogRecord
from discovery_ingest.schemas import TASK_KINDS, WORKER_DEFAULT_TASK_KINDS, CatalogueBatchItem
from discovery_ingest.worker.handler_table import handler_table
from discovery_ingest.worker.llm_drain import open_llm_drain
from discovery_ingest.worker.llm_extract import no_after_extract
from discovery_ingest.worker.policy import DrainPolicy

from llm_transport import ACCOUNT_ID, TOKEN
from llm_worker_fakes import MODEL, SERVICE, LlmApi, ScriptedLlm, resources

FIXTURES = Path(__file__).parent / "fixtures"
PVOG = FIXTURES / "pvog"
GOVDATA = FIXTURES / "govdata"
FEDERAL_ARS = "000000000000"
FEDERAL = uuid.UUID("11111111-1111-1111-1111-111111111101")
BASE = "https://pvog.example/suchdienst/api"
CATALOGUE_ID = uuid.UUID("22222222-2222-2222-2222-222222222202")
FIM_BASE = "https://fimportal.de"


def map_pvog(row: dict[str, object], **kwargs: object) -> CatalogueBatchItem:
    """Map a raw service row by way of the typed PVOG record."""
    return map_pvog_record(PvogRecord.model_validate(row), **kwargs)  # type: ignore[arg-type]


def map_govdata(row: dict[str, object], **kwargs: object) -> CatalogueBatchItem:
    """Map a raw OZG row by way of the typed GovData row."""
    return map_govdata_record(GovDataRow.model_validate(row), **kwargs)  # type: ignore[arg-type]


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _leaf_row(name: str) -> dict[str, object]:
    return _json(PVOG / name)["serviceDescriptions"]["content"][0]  # type: ignore[index]


def _pvog_pages(facades: dict[str, object], pages: dict[str, dict[str, object]]) -> tuple[PvogClient, list[str]]:
    """Return a client whose transport serves ``facades`` at the bootstrap and ``pages`` by URL, plus the URL log."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "facades=true" in str(request.url):
            return httpx.Response(200, json=facades)
        for marker, body in pages.items():
            if marker in str(request.url):
                return httpx.Response(200, json=body)
        return httpx.Response(404, text="not found")

    return PvogClient(BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler))), seen


def _page(*rows: object, last: object = True) -> dict[str, object]:
    return {"serviceDescriptions": {"content": list(rows), "last": last}}


def _leaf(code: str) -> dict[str, object]:
    return {"facades": {"personalMatters": [{"code": code}]}}


# --- 1. Mapper golden outputs --------------------------------------------------------------------------------------


def test_map_pvog_record_golden_live_shape_row() -> None:
    """map_pvog_record · the live shape row maps to an exact batch item and keeps the row verbatim."""
    row = _json(PVOG / "live_shape_row.json")

    item = map_pvog(row, jurisdiction_id=FEDERAL, personal_matter_code="1040300")  # type: ignore[arg-type]

    assert item.model_dump(mode="json") == {
        "source": "pvog",
        "external_id": "pvog:leika:99001040001000",
        "jurisdiction_id": str(FEDERAL),
        "title_i18n": {"de": "Live v7 Leistungsname"},
        "description_i18n": {"de": "Kurzer Teaser"},
        "portal_url": "https://service.example.bund.de/online",
        "raw_payload": {
            **row,
            "_personal_matter_code": "1040300",
        },
    }


def test_map_pvog_record_golden_leaf_row_without_portal_or_description() -> None:
    """map_pvog_record · a leaf row with only an lbId-style id, a title and no description."""
    row = _leaf_row("v7_page_leaf_a.json")

    item = map_pvog(row, jurisdiction_id=FEDERAL)  # type: ignore[arg-type]

    assert item.model_dump(mode="json") == {
        "source": "pvog",
        "external_id": "pvog:lb:SHARED-LB-001",
        "jurisdiction_id": str(FEDERAL),
        "title_i18n": {"de": "From leaf A"},
        "description_i18n": None,
        "portal_url": None,
        "raw_payload": {"id": "SHARED-LB-001", "lbId": "LB-SHARED", "title": "From leaf A"},
    }


def test_map_govdata_record_golden_ozg_page_first_row() -> None:
    """map_govdata_record · the first OZG page row maps to an exact batch item and keeps the row verbatim."""
    row = GovDataOzgClient.from_json_file(GOVDATA / "ozg_page.json").records[0].raw

    item = map_govdata(row, federal_jurisdiction_id=FEDERAL)

    assert item.model_dump(mode="json") == {
        "source": "govdata",
        "external_id": "govdata:leika:12345678901234",
        "jurisdiction_id": str(FEDERAL),
        "title_i18n": {"de": "Beispiel-Leistung"},
        "description_i18n": {"de": "Kurztext"},
        "portal_url": "https://example.bund.de/leistung",
        "raw_payload": dict(row),
    }
    assert item.raw_payload == row


def test_map_govdata_record_golden_open_pvog_live_shape_row() -> None:
    """map_govdata_record · the open-PVOG live row (integer ozgid) maps with the leika key as external id."""
    row = GovDataOzgClient.from_json_file(GOVDATA / "open_pvog_live_shape.json").records[0].raw

    item = map_govdata(row, federal_jurisdiction_id=FEDERAL)

    assert item.external_id == "govdata:leika:99003007001000"
    assert item.title_i18n == {"de": "Erlaubnis für die Teilnahme am Betäubungsmittelverkehr beantragen"}
    assert item.description_i18n == {"de": "Erlaubnis zum Verkehr mit Betäubungsmitteln Erteilung"}
    assert item.portal_url == "https://verwaltung.bund.de/leistung/example"
    assert item.raw_payload == row


def test_map_pvog_record_rejects_a_row_without_any_external_id() -> None:
    """map_pvog_record · no leika key and no id raises the mapping error with the existing message."""
    with pytest.raises(PvogMappingError, match="row has no external id"):
        map_pvog({"name": "orphan"}, jurisdiction_id=FEDERAL)  # type: ignore[arg-type]


def test_map_govdata_record_rejects_an_unsupported_ars() -> None:
    """map_govdata_record · a non-federal ars raises the mapping error with the ars in the message."""
    with pytest.raises(GovDataMappingError, match="unsupported ars jurisdiction scope: 099999999999"):
        map_govdata({"id": "x", "name": "y", "ars": "099999999999"}, federal_jurisdiction_id=FEDERAL)  # type: ignore[arg-type]


def test_map_govdata_record_rejects_a_row_without_title() -> None:
    """map_govdata_record · a row with no title key raises with the title message."""
    with pytest.raises(GovDataMappingError, match="row has no title"):
        map_govdata({"id": "x"}, federal_jurisdiction_id=FEDERAL)  # type: ignore[arg-type]


# --- 2. Ladder order -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"id": "1", "title": "T", "name": "N", "leistungsname": "L"}, "T"),
        ({"id": "1", "name": "N", "leistungsname": "L"}, "N"),
        ({"id": "1", "leistungsname": "L"}, "L"),
        ({"id": "1", "title": "  ", "name": "N"}, "N"),
    ],
)
def test_pvog_title_ladder_prefers_title_then_name_then_leistungsname(row: dict[str, object], expected: str) -> None:
    """map_pvog_record · the PVOG title ladder is title, name, leistungsname (blanks skipped)."""
    item = map_pvog(row, jurisdiction_id=FEDERAL)  # type: ignore[arg-type]

    assert item.title_i18n == {"de": expected}


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"leika_name": "A", "leistungsname": "B", "title": "C", "name": "D"}, "A"),
        ({"leistungsname": "B", "title": "C", "name": "D"}, "B"),
        ({"title": "C", "name": "D"}, "C"),
        ({"name": "D", "leika_bezeichnung": "E", "ozg_bezeichnung": "F"}, "D"),
        ({"leika_bezeichnung": "E", "ozg_bezeichnung": "F"}, "E"),
        ({"ozg_bezeichnung": "F"}, "F"),
    ],
)
def test_govdata_title_ladder_order(row: dict[str, object], expected: str) -> None:
    """map_govdata_record · the GovData title ladder follows the documented six-step order."""
    item = map_govdata({"id": "x", **row}, federal_jurisdiction_id=FEDERAL)  # type: ignore[arg-type]

    assert item.title_i18n == {"de": expected}


def test_description_ladders() -> None:
    """Description ladders · PVOG uses description, beschreibung, teaser; GovData uses beschreibung, description, leika, ozg."""
    pvog = map_pvog({"id": "1", "name": "N", "teaser": "T", "beschreibung": "B"}, jurisdiction_id=FEDERAL)  # type: ignore[arg-type]
    govdata = map_govdata(
        {"id": "x", "name": "N", "description": "D", "leika_bezeichnung": "L"},  # type: ignore[dict-item]
        federal_jurisdiction_id=FEDERAL,
    )

    assert pvog.description_i18n == {"de": "B"}
    assert govdata.description_i18n == {"de": "D"}


def test_steckbrief_label_prefers_title_then_titel_then_leistungsbezeichnung() -> None:
    """enrich · the steckbrief label is the first non-blank of title, titel, leistungsbezeichnung."""
    catalogue = _catalogue()

    def label(body: dict[str, object]) -> str | None:
        return fim_steckbrief_entity_request(catalogue, Steckbrief.from_object(body), fim_base_url=FIM_BASE).label

    assert label({"leistungsschluessel": "k", "title": "T", "titel": "Ti", "leistungsbezeichnung": "L"}) == "T"
    assert label({"leistungsschluessel": "k", "title": "  ", "titel": "Ti", "leistungsbezeichnung": "L"}) == "Ti"
    assert label({"leistungsschluessel": "k", "leistungsbezeichnung": "L"}) == "L"
    assert label({"leistungsschluessel": "k"}) is None


# --- 3. Leniency ---------------------------------------------------------------------------------------------------


def test_govdata_int_ozgid_becomes_external_id() -> None:
    """map_govdata_record · an integer ozgid without a leika key becomes the ozg external id as text."""
    item = map_govdata({"ozgid": 10641, "name": "N"}, federal_jurisdiction_id=FEDERAL)  # type: ignore[dict-item]

    assert item.external_id == "govdata:ozg:10641"


def test_pvog_int_id_maps_but_is_not_a_dedupe_key() -> None:
    """PVOG · an integer id maps (coerced to text) but iter_records skips it because the dedupe key is string-only."""
    item = map_pvog({"id": 7, "name": "N"}, jurisdiction_id=FEDERAL)  # type: ignore[arg-type]
    assert item.external_id == "pvog:lb:7"

    client, _seen = _pvog_pages(_leaf("LEAF_A"), {"personalMatters=LEAF_A": _page({"id": 7, "name": "N"})})
    assert list(client.iter_records(ars=FEDERAL_ARS)) == []


def test_pvog_blank_and_non_string_ids_are_skipped_in_the_dedupe_key() -> None:
    """PVOG · rows whose id and lbId are blank or non-string never reach the walk output."""
    rows = [{"id": "  ", "name": "blank"}, {"id": 3, "lbId": 4, "name": "ints"}, {"name": "absent"}]
    client, _seen = _pvog_pages(_leaf("LEAF_A"), {"personalMatters=LEAF_A": _page(*rows)})

    assert list(client.iter_records(ars=FEDERAL_ARS)) == []


def test_non_dict_entries_in_content_are_dropped() -> None:
    """PVOG · non-object entries in serviceDescriptions.content are ignored, the objects survive."""
    client, _seen = _pvog_pages(
        _leaf("LEAF_A"),
        {"personalMatters=LEAF_A": _page("junk", 5, {"id": "KEEP-1", "name": "N"}, ["x"])},
    )

    assert [record.raw["id"] for _code, record in client.iter_records(ars=FEDERAL_ARS)] == ["KEEP-1"]


def test_steckbrief_non_string_title_is_ignored() -> None:
    """enrich · a non-string title is ignored in favour of the next string field."""
    body = {"leistungsschluessel": "k", "title": 5, "titel": "Ti"}

    assert (
        fim_steckbrief_entity_request(_catalogue(), Steckbrief.from_object(body), fim_base_url=FIM_BASE).label == "Ti"
    )


def test_steckbrief_claims_follow_kurztext_and_title() -> None:
    """enrich · the metadata claim appears only with a real kurztext; the new_document claim carries the title."""
    body = {"leistungsschluessel": "k", "titel": "Ti", "kurztext": "Kurz"}
    claims = fim_steckbrief_claim_requests(
        _catalogue(),
        Steckbrief.from_object(body),
        entity_id=uuid.uuid4(),
        fim_base_url=FIM_BASE,  # type: ignore[arg-type]
    )

    assert [claim.kind for claim in claims] == ["metadata", "new_document"]
    assert claims[1].payload["title_i18n"] == {"de": "Ti"}


# --- 4. Page and bootstrap parsing ---------------------------------------------------------------------------------


def test_parse_v7_page_without_service_descriptions_is_last_and_empty() -> None:
    """PVOG walk · a page without serviceDescriptions yields nothing and does not request a next page."""
    client, seen = _pvog_pages(_leaf("LEAF_A"), {"personalMatters=LEAF_A": {"content": [{"id": "legacy"}]}})

    assert list(client.iter_records(ars=FEDERAL_ARS)) == []
    assert len([url for url in seen if "facades=false" in url]) == 1


@pytest.mark.parametrize(
    ("last", "expected_search_pages"),
    [(True, 1), (1, 1), (False, 2), (0, 2), (None, 2), ("no", 1)],
)
def test_last_flag_follows_truthiness_and_defaults_to_true(last: object, expected_search_pages: int) -> None:
    """PVOG walk · serviceDescriptions.last is read by truthiness; a missing flag counts as last."""
    first = _page({"id": "R1", "name": "N"}, last=last)
    second = _page({"id": "R2", "name": "N"}, last=True)
    client, seen = _pvog_pages(
        _leaf("LEAF_A"),
        {"personalMatters=LEAF_A&facades=false&size=100&page=0": first, "page=1": second},
    )

    list(client.iter_records(ars=FEDERAL_ARS))

    assert len([url for url in seen if "facades=false" in url]) == expected_search_pages


def test_facades_leaf_codes_are_sorted_unique_and_stripped() -> None:
    """PVOG bootstrap · leaf codes are stripped, blanks dropped, duplicates removed and sorted."""
    facades = {
        "facades": {
            "personalMatters": [
                {"code": " ZETA ", "children": []},
                {"code": "ALPHA", "children": [{"code": "NESTED_B"}, {"code": "  "}]},
                {"code": "ALPHA_PARENT_NOT_LEAF", "children": [{"code": "NESTED_A"}]},
                {"code": "ZETA"},
                "not-an-object",
            ],
        },
    }
    client, _seen = _pvog_pages(facades, {})

    assert client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS) == ["NESTED_A", "NESTED_B", "ZETA"]


def test_facades_missing_or_malformed_returns_no_codes() -> None:
    """PVOG bootstrap · a missing facades object or personalMatters list yields no codes."""
    for facades in ({}, {"facades": {}}, {"facades": {"personalMatters": "x"}}):
        client, _seen = _pvog_pages(facades, {})
        assert client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS) == []


# --- 5. Budget -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("max_pages", "expected_rows"), [(0, 0), (1, 0), (2, 1), (None, 2)])
def test_iter_records_max_pages_zero_one_two_none(max_pages: int | None, expected_rows: int) -> None:
    """PvogClient · max_pages counts the bootstrap and each search GET; None is unlimited."""
    client, _seen = _pvog_pages(
        _leaf("LEAF_A"),
        {
            "personalMatters=LEAF_A&facades=false&size=100&page=0": _page({"id": "R1", "name": "N"}, last=False),
            "page=1": _page({"id": "R2", "name": "N"}),
        },
    )

    assert len(list(client.iter_records(ars=FEDERAL_ARS, max_pages=max_pages))) == expected_rows


# --- 6. Negative paths ---------------------------------------------------------------------------------------------


def test_pvog_page_with_non_object_body_raises_the_client_error() -> None:
    """PvogClient · a JSON array as a search page raises PvogClientError, not ValueError."""
    client = PvogClient(
        BASE,
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])),
        ),
    )

    with pytest.raises(PvogClientError, match="expected JSON object"):
        list(client.iter_records(ars=FEDERAL_ARS))


def test_govdata_content_not_a_list_raises_value_error_with_the_existing_message(tmp_path: Path) -> None:
    """GovDataOzgClient · a page whose content is not a list raises the existing ValueError."""
    path = tmp_path / "page.json"
    path.write_text(json.dumps({"content": {"not": "a list"}}), encoding="utf-8")

    with pytest.raises(ValueError, match="expected top-level 'content' array in OZG JSON"):
        GovDataOzgClient.from_json_file(path)


def test_ckan_package_without_result_or_resources_raises_the_existing_messages() -> None:
    """GovDataCkanClient · a missing result and a missing resources list raise their existing messages."""

    def client_for(body: dict[str, object]) -> GovDataCkanClient:
        transport = httpx.MockTransport(lambda r: httpx.Response(200, json=body))
        return GovDataCkanClient("https://ckan.example", "pkg", http_client=httpx.Client(transport=transport))

    with pytest.raises(GovDataCkanError, match="missing result object"):
        next(client_for({"success": True}).iter_record_pages(max_pages=1))
    with pytest.raises(GovDataCkanError, match="has no resources list"):
        next(client_for({"result": {"resources": "nope"}}).iter_record_pages(max_pages=1))
    with pytest.raises(GovDataCkanError, match="no Leistungen resource URL"):
        next(
            client_for({"result": {"resources": [{"id": "other", "name": "x", "url": "u"}]}}).iter_record_pages(
                max_pages=1
            )
        )


def test_ckan_content_entries_are_dropped_when_not_objects() -> None:
    """GovDataCkanClient · non-object content entries are dropped from each feed page."""
    feed_page = {"content": ["junk", {"id": "a", "name": "A", "ozgid": "1"}]}
    package = {
        "result": {
            "resources": [{"id": "4b4fc7a2-8776-484d-834f-185590b181db", "url": "https://ckan.example/open-pvog?x=1"}]
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if "package_show" in str(request.url):
            return httpx.Response(200, json=package)
        return httpx.Response(200, json=feed_page)

    client = GovDataCkanClient(
        "https://ckan.example", "pkg", http_client=httpx.Client(transport=httpx.MockTransport(handler)), scope_ars=None
    )
    pages = list(client.iter_record_pages(max_pages=1))

    assert [[record.raw for record in page] for page in pages] == [[{"id": "a", "name": "A", "ozgid": "1"}]]


def test_steckbrief_without_leistungsschluessel_raises_value_error() -> None:
    """Steckbrief · a steckbrief without a usable leistungsschluessel raises ValueError with the existing message."""
    with pytest.raises(ValueError, match="steckbrief missing leistungsschluessel"):
        Steckbrief.from_object({"titel": "T"})
    with pytest.raises(ValueError, match="steckbrief missing leistungsschluessel"):
        Steckbrief.from_object({"leistungsschluessel": 42})


def test_stammtext_without_ids_raises_value_error() -> None:
    """Stammtext · a stammtext without redaktion_id or leistung_id raises ValueError with the existing messages."""
    with pytest.raises(ValueError, match="stammtext missing redaktion_id"):
        Stammtext.from_object({"leistung_id": "L"})
    with pytest.raises(ValueError, match="stammtext missing leistung_id"):
        Stammtext.from_object({"redaktion_id": "R", "leistung_id": " "})


@pytest.mark.parametrize("body", [b"\xff\xfe", b"not json", b"[1, 2]"])
def test_steckbrief_from_body_returns_none_for_invalid_utf8_non_json_and_non_object(body: bytes) -> None:
    """enrich_metadata · an unparseable or non-object steckbrief body yields None."""
    assert Steckbrief.from_body(body) is None


def test_steckbrief_from_missing_body_is_none() -> None:
    """enrich_metadata · no body at all yields None."""
    assert Steckbrief.from_body(None) is None


def test_fixture_key_mismatch_raises_fim_client_error_and_leika_mismatch_raises_leika_error(tmp_path: Path) -> None:
    """Fixture clients · a fixture whose key does not match the request raises the client's error."""
    from discovery_ingest.fim.client import FimClientError, FimSteckbriefClient

    steckbrief = tmp_path / "steckbrief.json"
    steckbrief.write_text(json.dumps({"leistungsschluessel": "AAA"}), encoding="utf-8")
    fim = FimSteckbriefClient.from_json_file(steckbrief, base_url=FIM_BASE)
    with pytest.raises(FimClientError, match="does not match"):
        fim.fetch_steckbrief("BBB")

    stammtext = tmp_path / "stammtext.json"
    stammtext.write_text(json.dumps({"redaktion_id": "R", "leistung_id": "L"}), encoding="utf-8")
    leika = LeikaStammtextClient.from_json_file(stammtext, base_url=FIM_BASE)
    with pytest.raises(LeikaClientError, match="fixture segments do not match"):
        leika.fetch_stammtext("R", "OTHER")


# --- 7. LLM JSON ---------------------------------------------------------------------------------------------------


def _small_taxonomy() -> Taxonomy:
    def term(code: str) -> dict[str, object]:
        return {"code": code, "name_i18n": {"de": code, "en": code}, "description_i18n": {"de": "d", "en": "d"}}

    return Taxonomy.model_validate({"domains": [term("DOM_A"), term("DOM_B")], "situations": [term("SIT_X")]})


def test_build_json_schema_golden_for_a_small_taxonomy() -> None:
    """build_json_schema · the full schema for a two-domain, one-situation taxonomy matches the golden file."""
    golden = json.loads((FIXTURES / "llm" / "page_extraction_schema_small.json").read_text(encoding="utf-8"))

    assert build_json_schema(_small_taxonomy()) == golden


def test_prepare_schema_inlines_nested_and_sibling_refs() -> None:
    """prepare_schema · nested refs, sibling keywords next to a ref and array items are all inlined."""
    schema = {
        "$defs": {
            "Leaf": {"type": "object", "properties": {"a": {"type": "string"}}},
            "Pair": {
                "type": "object",
                "properties": {"x": {"$ref": "#/$defs/Leaf"}, "y": {"$ref": "#/$defs/Leaf", "description": "why"}},
            },
        },
        "type": "object",
        "properties": {"p": {"$ref": "#/$defs/Pair"}, "q": {"type": "array", "items": {"$ref": "#/$defs/Leaf"}}},
    }

    assert prepare_schema(schema) == {
        "type": "object",
        "properties": {
            "p": {
                "type": "object",
                "properties": {
                    "x": {"type": "object", "properties": {"a": {"type": "string"}}},
                    "y": {"type": "object", "properties": {"a": {"type": "string"}}, "description": "why"},
                },
            },
            "q": {"type": "array", "items": {"type": "object", "properties": {"a": {"type": "string"}}}},
        },
    }


def test_prepare_schema_refuses_a_recursive_ref_with_its_name() -> None:
    """prepare_schema · a recursive ref raises ValueError that names the ref."""
    schema = {
        "$defs": {"Node": {"type": "object", "properties": {"child": {"$ref": "#/$defs/Node"}}}},
        "type": "object",
        "properties": {"root": {"$ref": "#/$defs/Node"}},
    }

    with pytest.raises(ValueError, match="#/\\$defs/Node"):
        prepare_schema(schema)


def test_run_body_messages_are_plain_dicts() -> None:
    """payloads · run_body and chat_body copy each message into a plain dict under messages."""
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    schema = {"type": "object"}

    run = run_body(messages, schema, 10)
    chat = chat_body("m", messages, schema, 10)

    assert run["messages"] == messages
    assert all(type(message) is dict for message in run["messages"])  # type: ignore[union-attr]
    assert chat["messages"] == messages
    assert run["response_format"] == {"type": "json_schema", "json_schema": schema}


# --- 8. Handlers ----------------------------------------------------------------------------------------------------


def test_every_task_kind_has_a_handler_when_all_parts_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    """handler_table · with extractors, browser parts and an LLM drain every task kind has a handler."""
    _llm_env(monkeypatch)
    api = LlmApi([])
    drain = open_llm_drain(
        DrainPolicy(kinds=("llm_extract",), neuron_budget=800),
        BudgetGuard(api.client(monkeypatch).budget),
        resources(ScriptedLlm(SERVICE)),
        no_after_extract,
    )
    assert drain is not None

    table = handler_table((), (object(), object(), lambda task, artifact: None), drain)  # type: ignore[arg-type]

    assert set(table) == set(TASK_KINDS)


def test_default_table_covers_worker_default_kinds() -> None:
    """handler_table · the worker default kinds always have a handler, even with no browser and no LLM."""
    table = handler_table((), (None, None, lambda task, artifact: None), None)

    assert set(WORKER_DEFAULT_TASK_KINDS) <= set(table)


# --- helpers -------------------------------------------------------------------------------------------------------


def _llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setenv("LLM_MODEL", MODEL)


def _catalogue() -> CatalogueExportItem:
    return CatalogueExportItem(
        id=CATALOGUE_ID,
        source="fim",
        portal_url=None,
        title_i18n={"de": "Katalog"},
        raw_payload={},
    )
