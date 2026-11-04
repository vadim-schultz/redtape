"""The ingest client facade: one shared connection, batching, bounded and scrubbed errors, secrets kept out of reprs."""

from __future__ import annotations

import json
import uuid
from contextlib import suppress
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.client.errors import MAX_ERROR_DETAIL_CHARS, TRUNCATION_MARK
from discovery_ingest.config import IngestSettings
from discovery_ingest.schemas import CatalogueBatchItem, RunFinishRequest
from pydantic import SecretStr, ValidationError

API_BASE = "https://redtape.test"
API_KEY = "test-machine-key"
PREFIX = "/api/v1/discovery/machine"
JURISDICTION = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_REAL_HTTPX_CLIENT = httpx.Client


def _item(external_id: str, title: str = "Antrag") -> CatalogueBatchItem:
    return CatalogueBatchItem(
        source="govdata",
        external_id=external_id,
        jurisdiction_id=JURISDICTION,
        title_i18n={"de": title},
    )


def _client(handler: Any) -> DiscoveryIngestClient:
    return DiscoveryIngestClient(API_BASE, SecretStr(API_KEY), transport=httpx.MockTransport(handler))


def test_one_http_client_serves_every_request(monkeypatch: pytest.MonkeyPatch) -> None:
    constructed: list[dict[str, Any]] = []

    def factory(**kwargs: Any) -> httpx.Client:
        constructed.append(kwargs)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
    client = _client(lambda request: httpx.Response(200, json={"items": [], "total": 0}))
    with client:
        client.budget.snapshot()
        client.budget.snapshot()
        with suppress(ValidationError):
            client.tasks.summary(kinds=("fetch_url",))
        client.runs.finish(
            uuid.uuid4(),
            RunFinishRequest(status="succeeded", claimed_count=0, completed_count=0, failed_count=0, skipped_count=0),
        )
    assert len(constructed) == 1


def test_base_url_trailing_slash_is_normalised() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"items": [], "total": 0})

    client = DiscoveryIngestClient(API_BASE + "/", SecretStr(API_KEY), transport=httpx.MockTransport(handler))
    client.budget.snapshot()
    assert seen[0].url.path == f"{PREFIX}/budgets"
    assert seen[0].headers["X-API-Key"] == API_KEY


def test_catalogue_upsert_batches_dedupes_and_chunks_by_batch_size() -> None:
    bodies: list[list[dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content)["items"])
        return httpx.Response(200, json={})

    items = [_item("row-0", "old")] + [_item(f"row-{i}") for i in range(1, 51)] + [_item("row-0", "new")]
    _client(handler).catalogue.upsert_batches(items)
    assert [len(body) for body in bodies] == [50, 1]
    assert bodies[0][0]["title_i18n"] == {"de": "new"}


def test_batch_size_outside_1_to_50_raises_value_error() -> None:
    client = _client(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ValueError, match="batch_size must be between 1 and 50"):
        client.catalogue.upsert_batches([_item("a")], batch_size=0)
    with pytest.raises(ValueError, match="batch_size must be between 1 and 50"):
        client.catalogue.upsert_batches([_item("a")], batch_size=51)


def test_empty_batch_raises() -> None:
    client = _client(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ValueError, match="items must not be empty"):
        client.catalogue.upsert_batches([])


def test_source_query_and_artifact_query_build_the_same_params_as_before() -> None:
    from discovery_ingest.artifacts import ArtifactQuery

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"items": [], "total": 0, "offset": 0, "limit": 5})

    client = _client(handler)
    client.artifacts.list(ArtifactQuery(host="verwaltung.bund.de", kind="html_snapshot", offset=5, limit=5))
    assert dict(seen[0].url.params) == {
        "host": "verwaltung.bund.de",
        "kind": "html_snapshot",
        "offset": "5",
        "limit": "5",
    }


def test_from_settings_sends_the_unwrapped_key() -> None:
    settings = SimpleNamespace(discovery_api_url=API_BASE, discovery_api_key=SecretStr(API_KEY))
    client = DiscoveryIngestClient.from_settings(settings)  # type: ignore[arg-type]
    assert client._http._client.headers["X-API-Key"] == API_KEY


def test_context_manager_closes_the_http_client() -> None:
    with DiscoveryIngestClient(API_BASE, SecretStr(API_KEY)) as client:
        assert not client._http._client.is_closed
    assert client._http._client.is_closed


def test_budget_guard_accepts_the_budget_resource() -> None:
    row = {
        "resource": "neurons",
        "period": "2026-10-26",
        "cap": 100,
        "used": 0,
        "remaining": 100,
        "exhausted": False,
    }
    client = _client(lambda request: httpx.Response(200, json={"items": [row]}))
    snapshot = BudgetGuard(client.budget).snapshot()
    assert snapshot is not None
    assert snapshot.items[0].remaining == 100


def test_error_detail_is_truncated_to_the_limit() -> None:
    huge = "<html>" + "x" * 1_000_000
    client = _client(lambda request: httpx.Response(500, text=huge))
    with pytest.raises(DiscoveryMachineApiError) as raised:
        client.budget.snapshot()
    assert len(raised.value.detail) <= MAX_ERROR_DETAIL_CHARS + len(TRUNCATION_MARK)
    assert raised.value.detail.endswith(TRUNCATION_MARK)


def test_error_detail_never_contains_the_api_key() -> None:
    body = f"bad key {API_KEY} echoed back"
    client = _client(lambda request: httpx.Response(401, text=body))
    with pytest.raises(DiscoveryMachineApiError) as raised:
        client.budget.snapshot()
    assert API_KEY not in raised.value.detail
    assert "<redacted>" in raised.value.detail
    assert API_KEY not in str(raised.value)
    assert API_KEY not in repr(raised.value)


def test_database_limit_survives_truncation() -> None:
    limit_body = json.dumps({"detail": "database_soft_limit", "padding": "x" * 5000})
    client = _client(lambda request: httpx.Response(507, text=limit_body))
    with pytest.raises(DiscoveryMachineApiError) as raised:
        client.budget.snapshot()
    assert raised.value.is_database_limit

    other = _client(lambda request: httpx.Response(507, text=json.dumps({"detail": "quota"})))
    with pytest.raises(DiscoveryMachineApiError) as other_raised:
        other.budget.snapshot()
    assert not other_raised.value.is_database_limit

    sentinel_500 = _client(lambda request: httpx.Response(500, text="database_soft_limit"))
    with pytest.raises(DiscoveryMachineApiError) as server_raised:
        sentinel_500.budget.snapshot()
    assert not server_raised.value.is_database_limit


def test_settings_repr_hides_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", API_KEY)
    settings = IngestSettings()
    client = DiscoveryIngestClient.from_settings(settings)
    assert API_KEY not in repr(settings)
    assert API_KEY not in repr(client)


def test_transport_error_is_not_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(httpx.ConnectError):
        _client(handler).budget.snapshot()


def test_invalid_success_body_raises_validation_error() -> None:
    client = _client(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ValidationError):
        client.budget.snapshot()
