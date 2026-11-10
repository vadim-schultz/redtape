"""Ingest wire models agree with the API models they mirror, read from the API's machine contract fixture.

The fixture is exported by ``apps/api/scripts/export_machine_contract.py``; its freshness is an API test.
"""

from __future__ import annotations

import importlib
import json
import re
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

import httpx
import pytest
from discovery_ingest import artifacts, edges, embedding_models, mentions, schemas
from discovery_ingest.budget_models import BUDGET_RESOURCES
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.json_types import JsonObject, JsonValue
from pydantic import BaseModel, ValidationError

from contract_compare import Direction, body_problems, compare
from test_machine_routes import ID, PREFIX, ROUTES, _recording_client, _upload

FIXTURE_PATH = Path(__file__).parents[2] / "api" / "tests" / "fixtures" / "discovery_machine_contract.json"
FIXTURE: JsonObject = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
Call = Callable[[DiscoveryIngestClient], object]
UNPAIRED_MODULES = (
    "schemas",
    "artifacts",
    "mentions",
    "edges",
    "emit_models",
    "budget_models",
    "embedding_models",
    "candidate_sources",
    "extract.llm.taxonomy",
    "pvog.crosswalk_wire",
)


@dataclass(frozen=True, slots=True)
class Pair:
    """One ingest model and the API model it mirrors, compared in one direction."""

    ingest: str
    """``module.Class`` under ``discovery_ingest``."""
    api: str
    """A key of the fixture's ``models`` section."""
    direction: Direction
    reads_subset: bool = False
    """The response is read only in part by ingest; the fields it leaves out are listed in the pair table."""
    api_enums: tuple[tuple[str, str], ...] = ()
    """``(field, enum name)``: API fields typed as a bare string, whose value set is the named enum."""


PAIRS: tuple[Pair, ...] = (
    Pair("schemas.CatalogueBatchItem", "machine.CatalogueBatchItem", "request"),
    Pair("schemas.CatalogueBatchRequest", "machine.CatalogueBatchRequest", "request"),
    Pair("schemas.CatalogueMachineRead", "machine.CatalogueMachineRead", "response"),
    Pair("schemas.EntityUpsertRequest", "machine.EntityUpsertRequest", "request"),
    Pair("schemas.EntityUpsertResponse", "machine.EntityUpsertResponse", "response"),
    Pair("schemas.ClaimAppendRequest", "machine.ClaimAppendRequest", "request"),
    Pair("schemas.ClaimAppendResponse", "machine.ClaimAppendResponse", "response"),
    Pair("schemas.TaskClaimRequest", "machine.TaskClaimRequest", "request"),
    Pair("schemas.TaskClaimResponse", "machine.TaskClaimResponse", "response"),
    Pair("schemas.ClaimedTask", "machine.ClaimedTaskRead", "response"),
    Pair("schemas.TaskSummary", "machine.TaskSummaryResponse", "response"),
    Pair("schemas.TaskEnqueueRequest", "machine.TaskEnqueueRequest", "request"),
    Pair("schemas.TaskEnqueueResponse", "machine.TaskEnqueueResponse", "response"),
    Pair("schemas.FetchLogAppendRequest", "machine.FetchLogAppendRequest", "request"),
    Pair("schemas.RunStartResponse", "machine.RunRead", "response", reads_subset=True),
    Pair("schemas.RunFinishRequest", "machine.RunFinishRequest", "request"),
    Pair("artifacts.ArtifactRead", "artifacts.ArtifactRead", "response", reads_subset=True),
    Pair("artifacts.ArtifactPage", "artifacts.ArtifactListResponse", "response"),
    Pair("artifacts.ArtifactStatus", "artifacts.ArtifactStatusResponse", "response"),
    Pair("mentions.MentionItem", "candidates.CandidateMentionItem", "request"),
    Pair("mentions.MentionsRequest", "candidates.CandidateMentionsRequest", "request"),
    Pair("mentions.MentionsResponse", "candidates.CandidateMentionsResponse", "response"),
    Pair("edges.EdgeItem", "candidate_edges.CandidateEdgeItem", "request"),
    Pair("edges.EdgesRequest", "candidate_edges.CandidateEdgesRequest", "request"),
    Pair("edges.EdgesResponse", "candidate_edges.CandidateEdgesResponse", "response"),
    Pair("edges.EdgeSkip", "candidate_edges.EdgeSkip", "response"),
    Pair("emit_models.EmitRequest", "candidate_emit.CandidateEmitRequest", "request"),
    Pair("emit_models.EmitResponse", "candidate_emit.CandidateEmitResponse", "response"),
    Pair("emit_models.EmitItem", "candidate_emit.CandidateEmitItemResult", "response"),
    Pair("emit_models.EmitConflict", "candidate_emit.EmitConflictRead", "response"),
    Pair("emit_models.EmitPreview", "candidate_emit.CandidateEmitPreview", "response"),
    Pair("emit_models.CandidatePage", "read.CandidateListResponse", "response", reads_subset=True),
    Pair("emit_models.CandidateSummary", "read.CandidateListItemRead", "response", reads_subset=True),
    Pair(
        "budget_models.BudgetRow",
        "budgets.BudgetRead",
        "response",
        api_enums=(("resource", "BudgetResource"),),
    ),
    Pair("budget_models.BudgetSnapshot", "budgets.BudgetListResponse", "response"),
    Pair("budget_models.BudgetReservation", "budgets.BudgetReserveResponse", "response"),
    Pair("candidate_sources.CandidateSourceRead", "candidate_sources.CandidateSourceRead", "response"),
    Pair("candidate_sources.CandidateSourcePage", "candidate_sources.CandidateSourceListResponse", "response"),
    Pair("extract.llm.taxonomy.Taxonomy", "taxonomy_read.VocabularyResponse", "response", reads_subset=True),
    Pair("pvog.crosswalk_wire.ServedVocabulary", "taxonomy_read.VocabularyResponse", "response"),
    Pair("pvog.crosswalk_wire.ServedCategory", "taxonomy_read.VocabularyTerm", "response", reads_subset=True),
    Pair("pvog.crosswalk_wire.ServedCrosswalk", "taxonomy_read.CrosswalkRead", "response"),
    Pair("pvog.crosswalk_wire.ServedLeafMapping", "taxonomy_read.PvogLeafMappingRead", "response"),
    Pair("extract.llm.taxonomy.TaxonomyTerm", "taxonomy_read.VocabularyTerm", "response"),
    Pair("embedding_models.EmbeddingClaimRequest", "search_machine.EmbeddingClaimRequest", "request"),
    Pair("embedding_models.ClaimedEmbeddingTask", "search_machine.ClaimedEmbeddingTask", "response"),
    Pair("embedding_models.EmbeddingClaimResponse", "search_machine.EmbeddingClaimResponse", "response"),
    Pair("embedding_models.EmbeddingCompleteItem", "search_machine.EmbeddingCompleteItem", "request"),
    Pair("embedding_models.EmbeddingCompleteRequest", "search_machine.EmbeddingCompleteRequest", "request"),
    Pair("embedding_models.EmbeddingItemResult", "search_machine.EmbeddingItemResult", "response"),
    Pair("embedding_models.EmbeddingCompleteResponse", "search_machine.EmbeddingCompleteResponse", "response"),
    Pair("embedding_models.EmbeddingFailRequest", "search_machine.EmbeddingFailRequest", "request"),
    Pair("embedding_models.EmbeddingFailResponse", "search_machine.EmbeddingFailResponse", "response"),
    Pair("embedding_models.EmbeddingReleaseRequest", "search_machine.EmbeddingReleaseRequest", "request"),
    Pair("embedding_models.EmbeddingReleaseResponse", "search_machine.EmbeddingReleaseResponse", "response"),
    Pair("embedding_models.EmbeddingSummary", "search_machine.EmbeddingSummaryResponse", "response"),
)
"""The 51 ingest-to-API pairs: 18 requests and 33 responses. Unpaired wire models are listed in ``UNPAIRED``."""

UNPAIRED: dict[str, str] = {
    "schemas.DrainReport": "a CLI report, never on the wire",
    "mentions.MentionDraft": "the base of MentionItem, covered through it",
}

ENUM_SETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("DiscoverySource", get_args(schemas.DiscoverySource)),
    ("DiscoveryTaskKind", get_args(schemas.DiscoveryTaskKind)),
    ("DiscoveryTaskStatus", get_args(schemas.DiscoveryTaskStatus)),
    ("DiscoveryClaimKind", get_args(schemas.DiscoveryClaimKind)),
    ("DiscoveryMentionRole", get_args(mentions.MentionRole)),
    ("DiscoveryArtifactKind", get_args(artifacts.ArtifactKind)),
    ("DiscoveryEdgeBasis", get_args(edges.EdgeBasis)),
    ("StopReason", get_args(schemas.StopReason)),
    ("EdgeSkipReason", get_args(edges.EdgeSkipReason)),
    ("BudgetResource", BUDGET_RESOURCES),
    ("EmbeddingOutcome", get_args(embedding_models.EmbeddingOutcome)),
    ("WorkTaskStatus", get_args(embedding_models.WorkTaskStatus)),
    ("LEGACY_TASK_KINDS", schemas.LEGACY_TASK_KINDS),
)

ROUTE_BODY: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/discovery/machine/runs"): "machine.RunStartRequest",
    ("POST", "/api/v1/discovery/machine/runs/{run_id}/finish"): "machine.RunFinishRequest",
    ("POST", "/api/v1/discovery/machine/catalogue/batch"): "machine.CatalogueBatchRequest",
    ("POST", "/api/v1/discovery/machine/entities"): "machine.EntityUpsertRequest",
    ("POST", "/api/v1/discovery/machine/claims"): "machine.ClaimAppendRequest",
    ("POST", "/api/v1/discovery/machine/candidates/mentions"): "candidates.CandidateMentionsRequest",
    ("POST", "/api/v1/discovery/machine/candidates/edges"): "candidate_edges.CandidateEdgesRequest",
    ("POST", "/api/v1/discovery/machine/candidates/emit"): "candidate_emit.CandidateEmitRequest",
    ("POST", "/api/v1/discovery/machine/tasks/claim"): "machine.TaskClaimRequest",
    ("POST", "/api/v1/discovery/machine/tasks"): "machine.TaskEnqueueRequest",
    ("POST", "/api/v1/discovery/machine/tasks/{task_id}/fetches"): "machine.FetchLogAppendRequest",
    ("POST", "/api/v1/discovery/machine/tasks/{task_id}/complete"): "machine.TaskCompleteRequest",
    ("POST", "/api/v1/discovery/machine/tasks/{task_id}/release"): "machine.TaskReleaseRequest",
    ("POST", "/api/v1/discovery/machine/tasks/{task_id}/fail"): "machine.TaskFailRequest",
    ("POST", "/api/v1/discovery/machine/budgets/{resource}/reserve"): "budgets.BudgetReserveRequest",
    ("POST", "/api/v1/discovery/machine/budgets/{resource}/adjust"): "budgets.BudgetAdjustRequest",
    ("POST", "/api/v1/discovery/machine/embeddings/claim"): "search_machine.EmbeddingClaimRequest",
    ("POST", "/api/v1/discovery/machine/embeddings/complete"): "search_machine.EmbeddingCompleteRequest",
    ("POST", "/api/v1/discovery/machine/embeddings/fail"): "search_machine.EmbeddingFailRequest",
    ("POST", "/api/v1/discovery/machine/embeddings/release"): "search_machine.EmbeddingReleaseRequest",
}
"""The routes that carry a JSON body, mapped to the API request model that validates it."""


def _object(value: JsonValue) -> JsonObject:
    """Return ``value`` as a JSON object, failing the test when it is not one."""
    if not isinstance(value, dict):
        raise TypeError(f"expected a JSON object in the contract fixture, got {type(value).__name__}")
    return value


def _strings(value: JsonValue) -> list[str]:
    """Return ``value`` as a list of strings, failing the test when it is not one."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError("expected a list of strings in the contract fixture")
    return list(value)


def _object_list(value: JsonValue) -> list[JsonObject]:
    """Return ``value`` as a list of JSON objects, failing the test when it is not one."""
    if not isinstance(value, list):
        raise TypeError("expected a list in the contract fixture")
    return [_object(item) for item in value]


MODELS = _object(FIXTURE["models"])
ENUMS = _object(FIXTURE["enums"])
FORMS = _object(FIXTURE["forms"])
FIXTURE_ROUTES: tuple[tuple[str, str], ...] = tuple(
    (str(route["method"]), str(route["path"])) for route in _object_list(FIXTURE["routes"])
)


def _api_schema(key: str) -> JsonObject:
    """Return the fixture's schema for the API model ``key``."""
    return _object(_object(MODELS[key])["schema"])


def _normal(path: str) -> str:
    """Return ``path`` without a trailing slash, since the API serves ``/candidates`` and the client calls ``/candidates/``."""
    return path.rstrip("/") or "/"


def _route_pattern(template: str) -> re.Pattern[str]:
    """Return a pattern that matches concrete paths for a templated path such as ``/tasks/{task_id}/fail``."""
    parts = re.split(r"(\{[^}]+\})", _normal(template))
    return re.compile("".join("[^/]+" if part.startswith("{") else re.escape(part) for part in parts))


def _template_of(method: str, path: str) -> str | None:
    """Return the fixture's route template that the concrete ``method`` and ``path`` match, or ``None``."""
    for route_method, template in FIXTURE_ROUTES:
        if route_method == method and _route_pattern(template).fullmatch(_normal(path)):
            return template
    return None


def _ingest_model(dotted: str) -> type[BaseModel]:
    """Return the ingest Pydantic model named ``module.Class`` under ``discovery_ingest``."""
    module_name, _, class_name = dotted.rpartition(".")
    model = getattr(importlib.import_module(f"discovery_ingest.{module_name}"), class_name)
    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise TypeError(f"{dotted} is not a Pydantic model")
    return model


def _record(call: Call) -> httpx.Request:
    """Run one client call against a recording transport and return the request it sent."""
    client, seen = _recording_client()
    with suppress(ValidationError):
        call(client)
    assert len(seen) == 1, "the call must send exactly one request"
    return seen[0]


def _call(name: str) -> Call:
    """Return the route-table call of the route named ``name``."""
    return next(call for route_name, call, _method, _path in ROUTES if route_name == name)


def _pair_id(pair: Pair) -> str:
    """Return the readable test id of a pair."""
    return f"{pair.ingest} <-> {pair.api}"


def _run_kind() -> str:
    """Return the run kind the client sends when it opens a run."""
    body = json.loads(_record(_call("runs.start")).content)
    return str(body["kind"])


def _walk_wire_models() -> set[str]:
    """Return the ``module.Class`` names of every Pydantic model defined in the ingest wire modules."""
    found: set[str] = set()
    for module_name in UNPAIRED_MODULES:
        module = importlib.import_module(f"discovery_ingest.{module_name}")
        for name, value in vars(module).items():
            if isinstance(value, type) and issubclass(value, BaseModel) and value.__module__ == module.__name__:
                found.add(f"{module_name}.{name}")
    return found


@pytest.mark.parametrize("pair", PAIRS, ids=_pair_id)
def test_model_pair_is_compatible(pair: Pair) -> None:
    """ingest pair · the ingest model and the API model agree in the pair's direction."""
    ingest_schema = _ingest_model(pair.ingest).model_json_schema(mode="validation")
    enums = {field_name: _strings(ENUMS[enum_name]) for field_name, enum_name in pair.api_enums}
    problems = compare(ingest_schema, _api_schema(pair.api), pair.direction, enums)
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("pair", [pair for pair in PAIRS if pair.direction == "response"], ids=_pair_id)
def test_unread_api_fields_are_declared_subsets(pair: Pair) -> None:
    """ingest pair · a response that ingest reads only in part is marked reads_subset, and only then."""
    ingest_fields = set(_object(_ingest_model(pair.ingest).model_json_schema(mode="validation")).get("properties", {}))
    api_fields = set(_object(_api_schema(pair.api)).get("properties", {}))
    unread = sorted(api_fields - ingest_fields)
    assert bool(unread) == pair.reads_subset, f"ingest does not read {unread}; the pair's reads_subset flag must match"


def test_every_pair_is_an_exported_model() -> None:
    """ingest pair · every API key a pair names is in the fixture, so no pair compares against nothing."""
    assert {pair.api for pair in PAIRS} <= set(MODELS)


def test_every_wire_model_in_ingest_is_paired_or_listed_as_unpaired() -> None:
    """ingest models · a new wire model must be paired with the API or listed as unpaired with a reason."""
    found = _walk_wire_models()
    paired = {pair.ingest for pair in PAIRS}
    assert found - paired - set(UNPAIRED) == set(), "new wire models without a pair or an unpaired reason"
    assert (paired | set(UNPAIRED)) - found == set(), "pair or unpaired entries that name no ingest model"


@pytest.mark.parametrize(("name", "ingest_values"), ENUM_SETS, ids=[name for name, _values in ENUM_SETS])
def test_enum_sets_are_equal(name: str, ingest_values: tuple[str, ...]) -> None:
    """enum sets · the ingest Literal or tuple holds exactly the values the API enum declares."""
    api_values = _strings(ENUMS[name])
    assert set(ingest_values) == set(api_values), f"ingest {sorted(ingest_values)} vs API {sorted(api_values)}"
    assert len(set(ingest_values)) == len(ingest_values), "a duplicate value would hide behind set equality"


def test_run_kind_sent_on_the_wire_is_an_api_value() -> None:
    """enum sets · the literal worker_drain that runs.start sends is a value of the API run kind."""
    assert _run_kind() in _strings(ENUMS["DiscoveryRunKind"])


@pytest.mark.parametrize(("name", "call", "method", "path"), ROUTES, ids=[route[0] for route in ROUTES])
def test_every_client_route_exists_in_the_api(name: str, call: Call, method: str, path: str) -> None:
    """routes · every route the client calls is a route the API serves."""
    assert _template_of(method, f"{PREFIX}{path}") is not None, f"{name}: {method} {path} is not in the API"


# A route whose body depends on an argument is recorded with the argument that sends the body.
BODY_VARIANTS: dict[str, Call] = {"tasks.complete": lambda client: client.tasks.complete(ID, note="login_wall")}
RECORDED_CALLS: tuple[tuple[str, str, str, Call], ...] = tuple(
    (name, method, path, BODY_VARIANTS.get(name, call)) for name, call, method, path in ROUTES
)


@pytest.mark.parametrize(
    ("name", "method", "path", "call"),
    [
        pytest.param(name, method, path, call, id=name)
        for name, method, path, call in RECORDED_CALLS
        if (method, _template_of(method, f"{PREFIX}{path}") or "") in ROUTE_BODY
    ],
)
def test_recorded_request_bodies_satisfy_the_api_request_schema(name: str, method: str, path: str, call: Call) -> None:
    """recorded bodies · the JSON the client sends on this route satisfies the API request model."""
    request = _record(call)
    template = _template_of(method, request.url.path)
    assert template is not None
    body: JsonValue = json.loads(request.content)
    assert body_problems(body, _api_schema(ROUTE_BODY[(method, template)])) == []


def test_every_json_body_route_has_an_api_request_model() -> None:
    """recorded bodies · the routes that send JSON are exactly the routes with an API request model."""
    sent: set[tuple[str, str]] = set()
    for _name, method, _path, call in RECORDED_CALLS:
        request = _record(call)
        if request.headers.get("content-type", "").startswith("application/json") and request.content:
            template = _template_of(method, request.url.path)
            assert template is not None
            sent.add((method, template))
    assert sent == set(ROUTE_BODY)


def test_artifact_upload_form_fields_match() -> None:
    """recorded bodies · the multipart fields of an artifact upload are fields of the API upload form."""
    request = _record(lambda client: client.artifacts.upload(ID, _upload()))
    sent = {
        field.decode("utf-8")
        for field in re.findall(rb'Content-Disposition: form-data; name="([^"]+)"', request.content)
    }
    form_fields = set(_strings(FORMS["ArtifactUploadForm"]))
    assert sent <= form_fields, f"ingest sends fields the API form does not declare: {sorted(sent - form_fields)}"
    assert {"file", "kind", "source_url"} <= sent, "the API requires these form fields"
