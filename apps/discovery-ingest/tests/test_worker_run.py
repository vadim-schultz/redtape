"""Worker drain records an explicit run through the machine API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.worker import run as run_module
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.run import recorded_run, run_recorded_drain
from pydantic import SecretStr, ValidationError

from run_stub import run_response

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client


def _patch_transport(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    transport = httpx.MockTransport(handler)

    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.worker.fetcher.httpx.Client", client_factory)


def _claimed_task() -> dict[str, object]:
    return {
        "id": str(uuid.uuid4()),
        "catalogue_service_id": str(uuid.uuid4()),
        "kind": "fetch_url",
        "target_url": "https://portal.example/s",
        "status": "claimed",
        "priority": 0,
        "lease_expires_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")


def test_worker_run_records_start_and_succeeded_finish_with_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    finishes: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request, finishes)
        if stub is not None:
            return stub
        if str(request.url).endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": []})
        return httpx.Response(404)

    _patch_transport(monkeypatch, handler)

    exit_code = main(["worker", "drain", "--max-tasks", "5"])

    assert exit_code == 0
    assert len(finishes) == 1
    assert finishes[0]["status"] == "succeeded"
    assert finishes[0]["claimed_count"] == 0
    assert finishes[0]["stop_reason"] == "queue_empty"
    assert finishes[0]["remaining_count"] is None


def test_worker_run_reports_batch_limit_when_the_batch_is_full(monkeypatch: pytest.MonkeyPatch) -> None:
    finishes: list[dict[str, object]] = []
    task = _claimed_task()

    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request, finishes)
        if stub is not None:
            return stub
        url = str(request.url)
        if url.endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": [task]})
        if url == task["target_url"]:
            raise httpx.ReadTimeout("timed out")
        if url.endswith("/fetches"):
            return httpx.Response(
                201, json={"id": str(uuid.uuid4()), "discovery_task_id": task["id"], "task_status": "claimed"}
            )
        return httpx.Response(200, json={"id": task["id"], "status": "failed", "last_error": "x"})

    _patch_transport(monkeypatch, handler)

    exit_code = main(["worker", "drain", "--max-tasks", "1"])

    assert exit_code == 0
    assert finishes[0]["status"] == "succeeded"
    assert finishes[0]["stop_reason"] == "batch_limit"
    assert (finishes[0]["claimed_count"], finishes[0]["failed_count"]) == (1, 1)


def test_worker_run_marks_run_failed_when_claim_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    finishes: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request, finishes)
        if stub is not None:
            return stub
        return httpx.Response(500, text="boom")

    _patch_transport(monkeypatch, handler)

    exit_code = main(["worker", "drain", "--max-tasks", "1"])

    assert exit_code == 1
    assert finishes[0]["status"] == "failed"
    assert finishes[0]["stop_reason"] == "error"
    assert "500" in str(finishes[0]["error_detail"])


def test_worker_run_does_not_drain_when_run_cannot_start(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(503, text="down")

    _patch_transport(monkeypatch, handler)

    exit_code = main(["worker", "drain", "--max-tasks", "1"])

    assert exit_code == 1
    assert seen == [f"{API_BASE}/api/v1/discovery/machine/runs"]


def _validation_error() -> ValidationError:
    from discovery_ingest.schemas import RunFinishRequest

    try:
        RunFinishRequest.model_validate(
            {"status": "bogus", "claimed_count": 0, "completed_count": 0, "failed_count": 0, "skipped_count": 0}
        )
    except ValidationError as err:
        return err
    raise AssertionError("expected a ValidationError")


def _recorded_client(monkeypatch: pytest.MonkeyPatch, finishes: list[dict[str, object]]) -> DiscoveryIngestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request, finishes)
        return stub if stub is not None else httpx.Response(404)

    _patch_transport(monkeypatch, handler)
    return DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))


@pytest.mark.parametrize(
    "raised",
    [ValueError("handler bug"), httpx.ConnectError("boom"), _validation_error(), KeyboardInterrupt()],
    ids=["ValueError", "ConnectError", "ValidationError", "KeyboardInterrupt"],
)
def test_the_run_is_finished_as_failed_when_the_drain_raises(
    monkeypatch: pytest.MonkeyPatch, raised: BaseException
) -> None:
    """recorded_run · any exception from the drain finishes the run failed once and re-raises the original error."""
    finishes: list[dict[str, object]] = []
    client = _recorded_client(monkeypatch, finishes)

    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise raised

    monkeypatch.setattr(run_module, "run_worker_drain", _raise)

    with pytest.raises(type(raised)):
        run_recorded_drain(client, PoliteUrlFetcher(), DrainPolicy())

    assert len(finishes) == 1
    assert finishes[0]["status"] == "failed"
    assert finishes[0]["stop_reason"] == "error"
    expected = "interrupted" if isinstance(raised, KeyboardInterrupt) else type(raised).__name__
    assert expected in str(finishes[0]["error_detail"])


def test_the_original_error_wins_when_closing_the_run_also_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """recorded_run · a 503 on the finish call never hides the original error, and the finish endpoint is called once."""
    finish_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/machine/runs"):
            return run_response(request, None)
        if "/finish" in url:
            finish_calls.append(url)
            return httpx.Response(503, text="finish unavailable")
        return httpx.Response(404)

    _patch_transport(monkeypatch, handler)
    client = DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))

    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise ValueError("handler bug")

    monkeypatch.setattr(run_module, "run_worker_drain", _raise)

    with pytest.raises(ValueError, match="handler bug"):
        run_recorded_drain(client, PoliteUrlFetcher(), DrainPolicy())

    assert len(finish_calls) == 1


def test_a_drain_that_returns_without_finishing_leaves_a_failed_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """recorded_run · a body that returns without calling finish is itself a failed run."""
    finishes: list[dict[str, object]] = []
    client = _recorded_client(monkeypatch, finishes)

    with recorded_run(client) as run:
        pass

    assert isinstance(run.run_id, uuid.UUID)
    assert len(finishes) == 1
    assert finishes[0]["status"] == "failed"
    assert "without finishing" in str(finishes[0]["error_detail"])
