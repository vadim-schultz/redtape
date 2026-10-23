"""Worker drain records an explicit run through the machine API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

from run_stub import run_response

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client


def _patch_transport(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    transport = httpx.MockTransport(handler)

    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", client_factory)
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
