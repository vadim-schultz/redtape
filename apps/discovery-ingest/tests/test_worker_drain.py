"""Worker drain CLI tests against machine API and polite fetcher."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

from run_stub import run_response

API_BASE = "https://redtape.test"
TASK_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CATALOGUE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
TARGET_URL = "https://portal.example/service/1"
_REAL_HTTPX_CLIENT = httpx.Client


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    """Patch httpx.Client for api_client and fetcher (shared httpx module binding)."""

    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.worker.fetcher.httpx.Client", client_factory)


def test_worker_drain_claims_task_posts_fetch_log_and_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """worker drain · claims task posts fetch log and completes."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")

    calls: list[tuple[str, str]] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request)
        if stub is not None:
            return stub
        url = str(request.url)
        calls.append((request.method, url))
        if url.endswith("/tasks/claim"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": str(TASK_ID),
                            "catalogue_service_id": str(CATALOGUE_ID),
                            "kind": "fetch_url",
                            "target_url": TARGET_URL,
                            "status": "claimed",
                            "priority": 0,
                            "lease_expires_at": datetime.now(UTC).isoformat(),
                        }
                    ]
                },
            )
        if url.endswith(f"/tasks/{TASK_ID}/fetches"):
            body = json.loads(request.content.decode())
            assert body == {
                "http_status": 200,
                "content_type": "text/html",
                "byte_length": 15,
                "error_message": None,
            }
            return httpx.Response(
                201, json={"id": str(uuid.uuid4()), "discovery_task_id": str(TASK_ID), "task_status": "claimed"}
            )
        if url.endswith(f"/tasks/{TASK_ID}/complete"):
            return httpx.Response(200, json={"id": str(TASK_ID), "status": "completed"})
        return httpx.Response(404, text=f"unexpected {url}")

    def combined_handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TARGET_URL:
            assert request.method == "GET"
            return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>ok</html>")
        return api_handler(request)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(combined_handler))

    exit_code = main(["worker", "drain", "--max-tasks", "1"])

    assert exit_code == 0
    methods_urls = [m for m, u in calls]
    assert "POST" in methods_urls
    assert any(u.endswith("/tasks/claim") for _, u in calls)
    assert any(u.endswith(f"/tasks/{TASK_ID}/fetches") for _, u in calls)
    assert any(u.endswith(f"/tasks/{TASK_ID}/complete") for _, u in calls)


def test_worker_drain_marks_fail_when_get_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """worker drain · marks fail when GET times out."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")

    def api_handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request)
        if stub is not None:
            return stub
        url = str(request.url)
        if url.endswith("/tasks/claim"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": str(TASK_ID),
                            "catalogue_service_id": str(CATALOGUE_ID),
                            "kind": "fetch_url",
                            "target_url": TARGET_URL,
                            "status": "claimed",
                            "priority": 0,
                            "lease_expires_at": datetime.now(UTC).isoformat(),
                        }
                    ]
                },
            )
        if url.endswith(f"/tasks/{TASK_ID}/fetches"):
            body = json.loads(request.content.decode())
            assert body["http_status"] is None
            assert body["error_message"] is not None
            return httpx.Response(
                201, json={"id": str(uuid.uuid4()), "discovery_task_id": str(TASK_ID), "task_status": "claimed"}
            )
        if url.endswith(f"/tasks/{TASK_ID}/fail"):
            body = json.loads(request.content.decode())
            assert "error" in body and body["error"]
            return httpx.Response(200, json={"id": str(TASK_ID), "status": "failed", "last_error": body["error"]})
        return httpx.Response(404, text=f"unexpected {url}")

    def combined_handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TARGET_URL:
            raise httpx.ReadTimeout("timed out")
        return api_handler(request)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(combined_handler))

    exit_code = main(["worker", "drain", "--max-tasks", "1"])

    assert exit_code == 0
