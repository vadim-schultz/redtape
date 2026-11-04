"""Worker enrich_metadata handler tests (chapter 8)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.policy import DrainPolicy
from pydantic import SecretStr

from drain_deps_for import deps_for
from run_stub import run_response

API_BASE = "https://redtape.test"
TASK_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CATALOGUE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ENTITY_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
FIM_ID = "99096049001001"
STECKBRIEF_URL = f"https://fimportal.de/api/v1/leistung-steckbriefe/{FIM_ID}"
STECKBRIEF_JSON = {
    "leistungsschluessel": FIM_ID,
    "titel": "Beispiel-Leistung",
    "kurztext": "Kurzbeschreibung aus FIM",
}
_REAL_HTTPX_CLIENT = httpx.Client


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.worker.fetcher.httpx.Client", client_factory)


def _claimed_enrich_task() -> dict[str, object]:
    return {
        "id": str(TASK_ID),
        "catalogue_service_id": str(CATALOGUE_ID),
        "kind": "enrich_metadata",
        "target_url": STECKBRIEF_URL,
        "status": "claimed",
        "priority": 200,
        "lease_expires_at": datetime.now(UTC).isoformat(),
    }


def test_enrich_metadata_fetches_steckbrief_and_posts_entity_and_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """enrich_metadata · fetches steckbrief and posts entity and claim."""
    posts: list[tuple[str, str, dict[str, object]]] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        path = request.url.path
        if url.endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": [_claimed_enrich_task()]})
        if path == f"/api/v1/discovery/machine/catalogue/{CATALOGUE_ID}":
            assert request.method == "GET"
            return httpx.Response(
                200,
                json={
                    "id": str(CATALOGUE_ID),
                    "source": "govdata",
                    "portal_url": "https://example.bund.de/leistung",
                    "title_i18n": {"de": "Beispiel-Leistung"},
                    "raw_payload": {"fim_id": FIM_ID},
                },
            )
        if path.endswith("/entities"):
            body = json.loads(request.content.decode())
            posts.append(("POST", path, body))
            return httpx.Response(
                201,
                json={
                    "id": str(ENTITY_ID),
                    "catalogue_service_id": str(CATALOGUE_ID),
                    "canonical_url": body["canonical_url"],
                    "created": True,
                },
            )
        if path.endswith("/claims"):
            body = json.loads(request.content.decode())
            posts.append(("POST", path, body))
            return httpx.Response(
                201,
                json={
                    "id": str(uuid.uuid4()),
                    "discovery_entity_id": str(ENTITY_ID),
                    "kind": body["kind"],
                },
            )
        if url.endswith(f"/tasks/{TASK_ID}/complete"):
            return httpx.Response(200, json={"id": str(TASK_ID), "status": "completed"})
        return httpx.Response(404, text=f"unexpected {url}")

    def combined_handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == STECKBRIEF_URL:
            return httpx.Response(200, json=STECKBRIEF_JSON)
        return api_handler(request)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(combined_handler))

    client = DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))
    report = run_worker_drain(deps_for(client, PoliteUrlFetcher(min_interval_per_host_s=0)), DrainPolicy(max_tasks=1))

    assert report.completed == 1
    entity_posts = [p for p in posts if p[1].endswith("/entities")]
    claim_posts = [p for p in posts if p[1].endswith("/claims")]
    assert len(entity_posts) == 1
    assert entity_posts[0][2]["catalogue_service_id"] == str(CATALOGUE_ID)
    assert len(claim_posts) >= 1


def test_enrich_metadata_fails_task_when_steckbrief_404(monkeypatch: pytest.MonkeyPatch) -> None:
    """enrich_metadata · fails task when steckbrief 404."""
    fail_calls: list[dict[str, object]] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        path = request.url.path
        if url.endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": [_claimed_enrich_task()]})
        if path == f"/api/v1/discovery/machine/catalogue/{CATALOGUE_ID}":
            return httpx.Response(
                200,
                json={
                    "id": str(CATALOGUE_ID),
                    "source": "govdata",
                    "portal_url": None,
                    "title_i18n": {"de": "Leistung"},
                    "raw_payload": {"fim_id": FIM_ID},
                },
            )
        if url.endswith(f"/tasks/{TASK_ID}/fail"):
            fail_calls.append(json.loads(request.content.decode()))
            return httpx.Response(
                200,
                json={
                    "id": str(TASK_ID),
                    "status": "failed",
                    "last_error": fail_calls[-1]["error"],
                },
            )
        return httpx.Response(404, text=f"unexpected {url}")

    def combined_handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == STECKBRIEF_URL:
            return httpx.Response(404, text="not found")
        return api_handler(request)

    _patch_httpx_client(monkeypatch, httpx.MockTransport(combined_handler))

    client = DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))
    report = run_worker_drain(deps_for(client, PoliteUrlFetcher(min_interval_per_host_s=0)), DrainPolicy(max_tasks=1))

    assert report.failed == 1
    assert len(fail_calls) == 1
    assert "error" in fail_calls[0] and fail_calls[0]["error"]


def test_enrich_metadata_fails_task_when_steckbrief_redirect_cannot_be_followed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """enrich_metadata · fails task when the steckbrief answers 3xx without a usable Location."""
    fail_calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == STECKBRIEF_URL:
            return httpx.Response(302)
        if url.endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": [_claimed_enrich_task()]})
        if request.url.path == f"/api/v1/discovery/machine/catalogue/{CATALOGUE_ID}":
            return httpx.Response(
                200,
                json={
                    "id": str(CATALOGUE_ID),
                    "source": "govdata",
                    "portal_url": None,
                    "title_i18n": {"de": "Leistung"},
                    "raw_payload": {"fim_id": FIM_ID},
                },
            )
        if url.endswith(f"/tasks/{TASK_ID}/fail"):
            fail_calls.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"id": str(TASK_ID), "status": "failed", "last_error": "x"})
        return httpx.Response(404, text=f"unexpected {url}")

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    client = DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))
    report = run_worker_drain(deps_for(client, PoliteUrlFetcher(min_interval_per_host_s=0)), DrainPolicy(max_tasks=1))

    assert (report.completed, report.failed) == (0, 1)
    assert "Location" in str(fail_calls[0]["error"])


def _drain_enrich_fail_bodies(monkeypatch: pytest.MonkeyPatch, steckbrief: Any) -> list[dict[str, object]]:
    fail_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request)
        if stub is not None:
            return stub
        url = str(request.url)
        if url == STECKBRIEF_URL:
            return steckbrief(request)
        if url.endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": [_claimed_enrich_task()]})
        if request.url.path == f"/api/v1/discovery/machine/catalogue/{CATALOGUE_ID}":
            raw = {"fim_id": FIM_ID}
            body = {
                "id": str(CATALOGUE_ID),
                "source": "govdata",
                "portal_url": None,
                "title_i18n": {"de": "L"},
                "raw_payload": raw,
            }
            return httpx.Response(200, json=body)
        if url.endswith("/fail"):
            fail_bodies.append(json.loads(request.content.decode()))
        return httpx.Response(200, json={"id": str(TASK_ID), "status": "failed", "last_error": "x"})

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))
    client = DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))
    run_worker_drain(deps_for(client, PoliteUrlFetcher(min_interval_per_host_s=0)), DrainPolicy(max_tasks=1))
    return fail_bodies


def _timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("timed out")


def test_enrich_metadata_reports_a_steckbrief_timeout_as_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    """enrich_metadata reports a steckbrief timeout as retryable."""
    bodies = _drain_enrich_fail_bodies(monkeypatch, _timeout)

    assert [body["retryable"] for body in bodies] == [True]


def test_enrich_metadata_reports_an_unparseable_steckbrief_as_permanent(monkeypatch: pytest.MonkeyPatch) -> None:
    """enrich_metadata never retries a steckbrief it cannot parse."""
    bodies = _drain_enrich_fail_bodies(monkeypatch, lambda request: httpx.Response(200, content=b"[]"))

    assert [body["retryable"] for body in bodies] == [False]
