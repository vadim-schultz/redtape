"""Machine crosswalk · parsed from the served vocabulary, fetched once through the client, refused when unusable."""

from __future__ import annotations

import copy
from collections.abc import Callable

import httpx
import pytest
from discovery_ingest.client.candidates_api import CandidatesAPI
from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.json_types import JsonObject
from discovery_ingest.pvog.category_mapping import CrosswalkError
from discovery_ingest.pvog.crosswalk_check import parse_crosswalk
from discovery_ingest.pvog.models import PvogSourcePath
from pydantic import SecretStr, ValidationError

from crosswalk_fakes import CROSSWALK, VOCABULARY

API_BASE = "https://redtape.test"
RETIREMENT_PATH = PvogSourcePath(
    root_code="1",
    root_label="Lebenslagen für Bürgerinnen und Bürger",
    parent_code="118",
    parent_label="Altersvorsorge und Ruhestand",
    leaf_code="1180100",
    leaf_label="Altersvorsorge",
    source_version="v7",
)


def _changed(change: Callable[[JsonObject], None]) -> JsonObject:
    """Return a copy of the served vocabulary after ``change`` has edited it."""
    body = copy.deepcopy(VOCABULARY)
    change(body)
    return body


def _leaf(body: JsonObject, leaf_code: str) -> JsonObject:
    """Return the served PVOG leaf mapping of ``leaf_code`` in ``body``."""
    crosswalk = body["crosswalk"]
    assert isinstance(crosswalk, dict)
    leaves = crosswalk["pvog_leaf_mappings"]
    assert isinstance(leaves, list)
    return next(item for item in leaves if isinstance(item, dict) and item["leaf_code"] == leaf_code)


def _taxonomy_client(handler: httpx.MockTransport) -> CandidatesAPI:
    return CandidatesAPI(MachineHttpClient(API_BASE, SecretStr("test-machine-key"), transport=handler))


def test_parsed_crosswalk_maps_a_complete_pvog_path_to_its_categories_and_versions() -> None:
    """machine crosswalk · a complete PVOG path maps to the served category with the served versions."""
    evidence = CROSSWALK.evidence_for_path(RETIREMENT_PATH)

    assert evidence is not None
    assert evidence.category_codes == ("retirement",)
    assert evidence.confidence == 0.95
    assert evidence.mapping_version == "category-contract-v1"
    assert CROSSWALK.pvog_source_version == "v7"


def test_parsed_crosswalk_refuses_a_leaf_that_names_an_unserved_category() -> None:
    """machine crosswalk · a leaf whose target is not in the served vocabulary is refused, naming the target."""
    body = _changed(lambda data: _leaf(data, "1180100").update(category_codes=["not-served"]))

    with pytest.raises(CrosswalkError, match="not-served"):
        parse_crosswalk(body)


def test_parsed_crosswalk_refuses_a_vocabulary_without_its_crosswalk() -> None:
    """machine crosswalk · a vocabulary that omits the crosswalk is malformed and refused."""
    body: JsonObject = {"categories": VOCABULARY["categories"]}

    with pytest.raises(CrosswalkError, match="malformed"):
        parse_crosswalk(body)


def test_client_fetches_the_crosswalk_from_the_machine_taxonomy_route() -> None:
    """candidates client · one GET of the machine taxonomy yields the validated crosswalk."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return httpx.Response(200, json=VOCABULARY)

    crosswalk = _taxonomy_client(httpx.MockTransport(handler)).crosswalk()

    assert requested == ["/api/v1/discovery/machine/taxonomy"]
    assert crosswalk.artifact_version == CROSSWALK.artifact_version


def test_client_refuses_an_unreachable_taxonomy_with_a_crosswalk_error() -> None:
    """candidates client · a transport failure is a crosswalk error, not a partial result."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(CrosswalkError, match="unavailable"):
        _taxonomy_client(httpx.MockTransport(handler)).crosswalk()


def test_client_refuses_a_failed_taxonomy_status_with_a_crosswalk_error() -> None:
    """candidates client · an error status from the taxonomy route is a crosswalk error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(CrosswalkError, match="unavailable"):
        _taxonomy_client(httpx.MockTransport(handler)).crosswalk()


def test_legacy_vocabulary_translates_through_the_crosswalk_it_is_given() -> None:
    """legacy translation · a legacy domain term resolves to the categories the crosswalk gives it."""
    legacy = {"domains": [{"code": "housing", "name_i18n": {"de": "Wohnen"}, "description_i18n": {}}]}

    taxonomy = Taxonomy.model_validate(legacy, context=CROSSWALK)

    assert taxonomy.category_codes == ("home-and-housing",)


def test_legacy_vocabulary_without_a_crosswalk_is_refused() -> None:
    """legacy translation · legacy fields with no crosswalk to translate them are refused, not dropped."""
    legacy = {"domains": [{"code": "housing", "name_i18n": {"de": "Wohnen"}, "description_i18n": {}}]}

    with pytest.raises(ValidationError, match="crosswalk"):
        Taxonomy.model_validate(legacy)
