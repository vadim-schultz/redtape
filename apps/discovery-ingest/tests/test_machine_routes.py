"""The machine routes on the wire: every facade operation sends its method and path under the machine prefix.

Responses are minimal (``{}``): a model that cannot validate such a body raises after the request was sent, so the
route is pinned without modelling every answer. Answer shapes are pinned by the resource tests.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime

import httpx
import pytest
from discovery_ingest.artifacts import ArtifactQuery, ArtifactUpload
from discovery_ingest.budget_models import BudgetResource
from discovery_ingest.candidate_sources import SourceQuery
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.edges import EdgeItem
from discovery_ingest.mentions import MentionItem
from discovery_ingest.pvog.category_mapping import CrosswalkError
from discovery_ingest.schemas import (
    CatalogueBatchItem,
    ClaimAppendRequest,
    EntityUpsertRequest,
    FetchLogAppendRequest,
    RunFinishRequest,
    TaskEnqueueRequest,
)
from pydantic import SecretStr, ValidationError

API_BASE = "https://redtape.test"
API_KEY = "test-machine-key"
PREFIX = "/api/v1/discovery/machine"
ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
JURISDICTION = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
RESOURCE: BudgetResource = "neurons"
Call = Callable[[DiscoveryIngestClient], object]


def _catalogue_item() -> CatalogueBatchItem:
    return CatalogueBatchItem(
        source="govdata",
        external_id="row-1",
        jurisdiction_id=JURISDICTION,
        title_i18n={"de": "Antrag"},
    )


def _mention() -> MentionItem:
    return MentionItem(
        catalogue_service_id=ID,
        title_i18n={"de": "Geburtsurkunde"},
        role="required",
        excerpt="Geburtsurkunde",
        source_field="description",
        extractor="test",
        extractor_version="1",
    )


def _edge() -> EdgeItem:
    return EdgeItem(
        catalogue_service_id=ID,
        parent_title_i18n={"de": "Antrag"},
        required_title_i18n={"de": "Geburtsurkunde"},
        basis="explicit",
        excerpt="Antrag",
        extractor="test",
        extractor_version="1",
    )


def _upload() -> ArtifactUpload:
    return ArtifactUpload(
        kind="html_snapshot",
        data=b"<html></html>",
        content_type="text/html",
        source_url="https://x.test/a",
        final_url=None,
        fetched_at=datetime(2026, 10, 27, tzinfo=UTC),
    )


ROUTES: list[tuple[str, Call, str, str]] = [
    ("runs.start", lambda c: c.runs.start(), "POST", "/runs"),
    (
        "runs.finish",
        lambda c: c.runs.finish(
            ID,
            RunFinishRequest(status="succeeded", claimed_count=0, completed_count=0, failed_count=0, skipped_count=0),
        ),
        "POST",
        f"/runs/{ID}/finish",
    ),
    (
        "catalogue.upsert_batches",
        lambda c: c.catalogue.upsert_batches([_catalogue_item()]),
        "POST",
        "/catalogue/batch",
    ),
    ("catalogue.get", lambda c: c.catalogue.get(ID), "GET", f"/catalogue/{ID}"),
    (
        "catalogue.upsert_entity",
        lambda c: c.catalogue.upsert_entity(
            EntityUpsertRequest(catalogue_service_id=ID, canonical_url="https://x.test/a")
        ),
        "POST",
        "/entities",
    ),
    (
        "catalogue.append_claim",
        lambda c: c.catalogue.append_claim(ClaimAppendRequest(discovery_entity_id=ID, kind="metadata")),
        "POST",
        "/claims",
    ),
    ("candidates.post_mentions", lambda c: c.candidates.post_mentions([_mention()]), "POST", "/candidates/mentions"),
    ("candidates.post_edges", lambda c: c.candidates.post_edges([_edge()]), "POST", "/candidates/edges"),
    (
        "candidates.list_staged",
        lambda c: c.candidates.list_staged(min_mentions=2, limit=10),
        "GET",
        "/candidates/",
    ),
    ("candidates.preview_emit", lambda c: c.candidates.preview_emit(ID), "GET", f"/candidates/{ID}/emit-preview"),
    ("candidates.emit", lambda c: c.candidates.emit([ID]), "POST", "/candidates/emit"),
    (
        "candidates.list_sources",
        lambda c: c.candidates.list_sources(
            SourceQuery(host=None, missing=None, candidate_id=None, service_ids=[], offset=0, limit=10)
        ),
        "GET",
        "/candidates/sources",
    ),
    ("candidates.taxonomy", lambda c: c.candidates.taxonomy(), "GET", "/taxonomy"),
    ("candidates.crosswalk", lambda c: _crosswalk_or_none(c), "GET", "/taxonomy"),
    ("tasks.claim", lambda c: c.tasks.claim(limit=5, kinds=("fetch_url",)), "POST", "/tasks/claim"),
    (
        "tasks.summary",
        lambda c: c.tasks.summary(kinds=("fetch_url", "enrich_metadata")),
        "GET",
        "/tasks/summary",
    ),
    (
        "tasks.enqueue",
        lambda c: c.tasks.enqueue(
            TaskEnqueueRequest(catalogue_service_id=ID, kind="fetch_url", target_url="https://x.test/a")
        ),
        "POST",
        "/tasks",
    ),
    (
        "tasks.append_fetch",
        lambda c: c.tasks.append_fetch(ID, FetchLogAppendRequest(http_status=200)),
        "POST",
        f"/tasks/{ID}/fetches",
    ),
    ("tasks.complete", lambda c: c.tasks.complete(ID), "POST", f"/tasks/{ID}/complete"),
    ("tasks.release", lambda c: c.tasks.release(ID, "limit"), "POST", f"/tasks/{ID}/release"),
    ("tasks.fail", lambda c: c.tasks.fail(ID, error="boom"), "POST", f"/tasks/{ID}/fail"),
    ("artifacts.upload", lambda c: c.artifacts.upload(ID, _upload()), "POST", f"/tasks/{ID}/artifacts"),
    ("artifacts.status", lambda c: c.artifacts.status(), "GET", "/artifacts/status"),
    ("artifacts.content", lambda c: c.artifacts.content(ID), "GET", f"/artifacts/{ID}/content"),
    (
        "artifacts.list",
        lambda c: c.artifacts.list(ArtifactQuery(host=None, kind="html_snapshot", offset=0, limit=10)),
        "GET",
        "/artifacts",
    ),
    ("budget.snapshot", lambda c: c.budget.snapshot(), "GET", "/budgets"),
    ("budget.reserve", lambda c: c.budget.reserve(RESOURCE, 10.0), "POST", f"/budgets/{RESOURCE}/reserve"),
    ("budget.adjust", lambda c: c.budget.adjust(RESOURCE, -2.0), "POST", f"/budgets/{RESOURCE}/adjust"),
    ("budget.exhaust", lambda c: c.budget.exhaust(RESOURCE), "POST", f"/budgets/{RESOURCE}/exhaust"),
]


def _crosswalk_or_none(client: DiscoveryIngestClient) -> object:
    """Call the crosswalk route; the recording client answers ``{}``, which is an invalid crosswalk and is refused."""
    try:
        return client.candidates.crosswalk()
    except CrosswalkError:
        return None


def _recording_client(status: int = 200) -> tuple[DiscoveryIngestClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json={})

    client = DiscoveryIngestClient(API_BASE, SecretStr(API_KEY), transport=httpx.MockTransport(handler))
    return client, seen


@pytest.mark.parametrize(
    ("call", "method", "path"),
    [pytest.param(call, method, path, id=name) for name, call, method, path in ROUTES],
)
def test_route_table_matches_the_wire(call: Call, method: str, path: str) -> None:
    client, seen = _recording_client()
    # The empty answer does not validate; the request is what is pinned here.
    with suppress(ValidationError):
        call(client)
    assert len(seen) == 1
    assert seen[0].method == method
    assert seen[0].url.path == f"{PREFIX}{path}"
    assert seen[0].headers["X-API-Key"] == API_KEY


def test_enqueue_drops_none_fields() -> None:
    client, seen = _recording_client()
    with suppress(ValidationError):
        client.tasks.enqueue(TaskEnqueueRequest(catalogue_service_id=ID, kind="fetch_url", target_url="https://x.test"))
    body = seen[0].read().decode()
    assert "input_key" not in body
    assert "artifact_id" not in body


def test_summary_sends_kinds_as_repeated_param() -> None:
    client, seen = _recording_client()
    with suppress(ValidationError):
        client.tasks.summary(kinds=("fetch_url", "enrich_metadata"))
    assert seen[0].url.params.get_list("kinds") == ["fetch_url", "enrich_metadata"]


def test_sources_query_omits_none_and_repeats_service_ids() -> None:
    client, seen = _recording_client()
    first, second = uuid.uuid4(), uuid.uuid4()
    with suppress(ValidationError):
        client.candidates.list_sources(
            SourceQuery(
                host=None, missing="screenshot", candidate_id=None, service_ids=[first, second], offset=0, limit=7
            )
        )
    params = seen[0].url.params
    assert "host" not in params
    assert "candidate_id" not in params
    assert params["missing"] == "screenshot"
    assert params.get_list("catalogue_service_id") == [str(first), str(second)]
    assert params["limit"] == "7"


ARTIFACT_ROW = {
    "id": str(ID),
    "catalogue_service_id": str(ID),
    "discovery_task_id": None,
    "kind": "html_snapshot",
    "sha256": "0" * 64,
    "content_type": "text/html",
    "byte_size": 1,
    "source_url": "https://x.test/a",
    "final_url": None,
    "fetched_at": "2026-10-27T00:00:00Z",
}


def _upload_created_flag(status: int) -> bool:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=ARTIFACT_ROW)

    client = DiscoveryIngestClient(API_BASE, SecretStr(API_KEY), transport=httpx.MockTransport(handler))
    return client.artifacts.upload(ID, _upload()).created


def test_upload_201_is_created_and_200_is_a_match() -> None:
    assert _upload_created_flag(201) is True
    assert _upload_created_flag(200) is False


def test_reserve_409_is_an_answer_not_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"granted": False, "remaining": 0.0})

    client = DiscoveryIngestClient(API_BASE, SecretStr(API_KEY), transport=httpx.MockTransport(handler))
    answer = client.budget.reserve(RESOURCE, 10.0)
    assert answer.granted is False


def test_error_status_raises_with_the_body_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="no such task")

    client = DiscoveryIngestClient(API_BASE, SecretStr(API_KEY), transport=httpx.MockTransport(handler))
    with pytest.raises(DiscoveryMachineApiError) as raised:
        client.tasks.fail(ID, error="boom")
    assert raised.value.status_code == 404
    assert raised.value.detail == "no such task"
