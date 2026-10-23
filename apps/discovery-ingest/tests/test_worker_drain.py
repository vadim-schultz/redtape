"""Worker drain CLI tests against machine API and polite fetcher."""

from __future__ import annotations

import itertools
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


def _task_json(task_id: uuid.UUID, url: str = TARGET_URL) -> dict[str, object]:
    return {
        "id": str(task_id),
        "catalogue_service_id": str(CATALOGUE_ID),
        "kind": "fetch_url",
        "target_url": url,
        "status": "claimed",
        "priority": 0,
        "lease_expires_at": datetime.now(UTC).isoformat(),
    }


def _queue_handler(
    batches: list[list[dict[str, object]]],
    claims: list[int],
    finishes: list[dict[str, object]],
    *,
    fetch_status: int = 200,
) -> Any:
    """Serve ``batches`` one per claim call, then empty; count claims."""

    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request, finishes)
        if stub is not None:
            return stub
        url = str(request.url)
        if url == TARGET_URL:
            return httpx.Response(fetch_status, headers={"content-type": "text/html"}, content=b"x")
        if url.endswith("/tasks/claim"):
            items = batches[claims[0]] if claims[0] < len(batches) else []
            claims[0] += 1
            return httpx.Response(200, json={"items": items})
        if url.endswith("/fetches"):
            return httpx.Response(
                201, json={"id": str(uuid.uuid4()), "discovery_task_id": str(TASK_ID), "task_status": "claimed"}
            )
        return httpx.Response(200, json={"id": str(TASK_ID), "status": "completed", "last_error": "x"})

    return handler


@pytest.fixture
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")


def _two_batches() -> list[list[dict[str, object]]]:
    return [[_task_json(uuid.uuid4()), _task_json(uuid.uuid4())], [_task_json(uuid.uuid4())]]


def test_worker_drain_processes_two_batches_and_aggregates_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], _env: None
) -> None:
    """worker drain processes two batches and aggregates the report."""
    claims, finishes = [0], []
    _patch_httpx_client(monkeypatch, httpx.MockTransport(_queue_handler(_two_batches(), claims, finishes)))

    exit_code = main(["worker", "drain", "--max-tasks", "2", "--max-batches", "2"])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert claims[0] == 2
    assert (report["batches"], report["claimed"], report["completed"], report["failed"]) == (2, 3, 3, 0)
    assert report["run_id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert report["stop_reason"] == "batch_limit"
    assert report["succeeded"] is True


def test_worker_drain_stops_after_empty_claim_response(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], _env: None
) -> None:
    """worker drain stops after an empty claim response."""
    claims, finishes = [0], []
    _patch_httpx_client(monkeypatch, httpx.MockTransport(_queue_handler(_two_batches(), claims, finishes)))

    exit_code = main(["worker", "drain", "--max-tasks", "2", "--max-batches", "10"])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert claims[0] == 3
    assert report["stop_reason"] == "queue_empty"
    assert report["batches"] == 3
    assert finishes[0]["stop_reason"] == "queue_empty"


@pytest.mark.parametrize(
    "flags",
    [["--max-batches", "0"], ["--max-batches", "-1"], ["--time-budget-seconds", "0"], ["--max-tasks", "51"]],
)
def test_worker_drain_rejects_non_positive_bounds_before_claiming(
    monkeypatch: pytest.MonkeyPatch, flags: list[str], _env: None
) -> None:
    """worker drain rejects non-positive batch or time bounds before claiming."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(500)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    assert main(["worker", "drain", *flags]) == 2
    assert seen == []


def test_worker_drain_rejects_non_numeric_bound(_env: None) -> None:
    """worker drain rejects a non-numeric bound at argument parsing."""
    with pytest.raises(SystemExit):
        main(["worker", "drain", "--max-batches", "many"])


def test_worker_drain_stops_at_time_budget_without_speculative_claim(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], _env: None
) -> None:
    """worker drain stops at the configured bound and reports remaining work."""
    claims, finishes = [0], []
    ticks = itertools.chain([0.0], itertools.repeat(5.0))
    monkeypatch.setattr("discovery_ingest.worker.drain.time.monotonic", lambda: next(ticks))
    _patch_httpx_client(monkeypatch, httpx.MockTransport(_queue_handler(_two_batches(), claims, finishes)))

    exit_code = main(["worker", "drain", "--max-tasks", "2", "--max-batches", "9", "--time-budget-seconds", "1"])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert claims[0] == 1
    assert report["stop_reason"] == "time_budget"
    assert report["remaining"] is None
    assert report["remaining_unknown"] is True


def test_worker_drain_default_is_a_single_batch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], _env: None
) -> None:
    """worker drain without new bounds claims exactly one batch."""
    claims, finishes = [0], []
    _patch_httpx_client(monkeypatch, httpx.MockTransport(_queue_handler(_two_batches(), claims, finishes)))

    assert main(["worker", "drain"]) == 0
    assert claims[0] == 1
    assert json.loads(capsys.readouterr().out)["stop_reason"] == "batch_limit"


def test_worker_drain_finishes_run_successfully_with_task_failures_counted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], _env: None
) -> None:
    """worker drain finishes a successful bounded run with task failures counted."""
    claims, finishes = [0], []
    handler = _queue_handler(_two_batches(), claims, finishes, fetch_status=500)
    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(["worker", "drain", "--max-tasks", "2", "--max-batches", "2"])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert (report["failed"], report["succeeded"]) == (3, True)
    assert finishes[0]["status"] == "succeeded"
    assert finishes[0]["failed_count"] == 3


def test_worker_drain_marks_run_failed_when_second_claim_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], _env: None
) -> None:
    """worker drain marks the run failed when claim API fails mid-drain."""
    finishes: list[dict[str, object]] = []
    claims = [0]
    inner = _queue_handler(_two_batches(), claims, finishes)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/tasks/claim") and claims[0] >= 1:
            return httpx.Response(500, text="boom")
        return inner(request)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(["worker", "drain", "--max-tasks", "2", "--max-batches", "3"])

    assert exit_code == 1
    assert capsys.readouterr().out == ""
    assert [f["status"] for f in finishes] == ["failed"]
    assert finishes[0]["stop_reason"] == "error"


def test_worker_drain_sends_the_configured_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """worker drain · fetcher identifies itself with the configured contact url."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("BOT_CONTACT_URL", "https://ops.example/bot")
    agents: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request)
        if stub is not None:
            return stub
        if request.url.host == "portal.example":
            agents.append(request.headers["user-agent"])
            return httpx.Response(200, content=b"ok")
        if str(request.url).endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": [_task_json(TASK_ID)]})
        if str(request.url).endswith("/fetches"):
            return httpx.Response(
                201, json={"id": str(uuid.uuid4()), "discovery_task_id": str(TASK_ID), "task_status": "claimed"}
            )
        return httpx.Response(200, json={"id": str(TASK_ID), "status": "completed"})

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    assert main(["worker", "drain", "--max-tasks", "1"]) == 0
    assert agents
    assert set(agents) == {"RedtapeBot/1.0 (+https://ops.example/bot)"}
