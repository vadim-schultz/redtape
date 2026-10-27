"""Fakes for the render worker tests: a scripted machine API, a scripted browser and a robots-only fetcher."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.browser.errors import BrowserError
from discovery_ingest.browser.port import RenderedPage, ScreenshotImage
from discovery_ingest.worker.fetcher import PoliteUrlFetcher

from run_stub import run_response

API_BASE = "https://redtape.test"
CATALOGUE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_REAL_HTTPX_CLIENT = httpx.Client


def task_json(
    task_id: uuid.UUID, url: str = "https://portal.example/service/1", kind: str = "render_page"
) -> dict[str, object]:
    """Return a claimed task as the claim route serves it."""
    return {
        "id": str(task_id),
        "catalogue_service_id": str(CATALOGUE_ID),
        "kind": kind,
        "target_url": url,
        "status": "claimed",
        "priority": 100,
        "lease_expires_at": datetime.now(UTC).isoformat(),
    }


def artifact_json() -> dict[str, object]:
    """Return the metadata the upload route answers with."""
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "catalogue_service_id": str(CATALOGUE_ID),
        "discovery_task_id": None,
        "kind": "html_snapshot",
        "storage_key": "k",
        "sha256": "abc",
        "content_type": "text/html",
        "byte_size": 5,
        "source_url": "https://portal.example/service/1",
        "final_url": None,
        "fetched_at": now,
        "created_at": now,
    }


class FakeApi:
    """A machine API that serves batches of tasks and records every call as ``(name, task_id, body)``."""

    def __init__(self, batches: list[list[dict[str, object]]], *, ledger_remaining: float | None = 480.0) -> None:
        self.batches = batches
        self.ledger_remaining = ledger_remaining
        self.ledger_exhausted = False
        self.upload_status = 201
        self.upload_detail = ""
        self.storage_enabled = True
        self.status_http = 200
        self.enqueue_status = 200
        self.pages: dict[str, httpx.Response] = {}
        self.cloudflare: Callable[[httpx.Request], httpx.Response] | None = None
        self.finishes: list[dict[str, object]] = []
        self.calls: list[tuple[str, str, Any]] = []
        self.uploads: list[httpx.Request] = []
        self.stored: list[dict[str, object]] = []
        self.enqueued: set[tuple[str, str, str | None]] = set()

    def named(self, name: str) -> list[tuple[str, Any]]:
        """Return ``(task_id, body)`` of every recorded call of kind ``name``."""
        return [(task, body) for call, task, body in self.calls if call == name]

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Answer one request: the machine API, Cloudflare, or a target page."""
        if request.url.host == "api.cloudflare.com" and self.cloudflare is not None:
            return self.cloudflare(request)
        if request.url.host != "redtape.test":
            return self.pages.get(str(request.url), httpx.Response(404))
        if (stub := run_response(request, self.finishes)) is not None:
            return stub
        path = request.url.path
        if (match := re.search(r"/tasks/([0-9a-f-]{36})/(\w+)$", path)) is not None:
            return self._task_route(request, match.group(1), match.group(2))
        if "/budgets" in path:
            return self._budget_route(request)
        if path.endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": self.batches.pop(0) if self.batches else []})
        if path.endswith("/artifacts/status"):
            status = {"storage_enabled": self.storage_enabled, "bytes_used": 0, "bytes_cap": 100}
            return httpx.Response(self.status_http, json=status)
        if path.endswith("/machine/tasks") and request.method == "POST":
            return self._enqueue(request)
        return httpx.Response(500, text="no stub")

    def _enqueue(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(("enqueue", "", json.loads(request.content)))
        if self.enqueue_status >= 400:
            return httpx.Response(self.enqueue_status, text="enqueue refused")
        body = self.calls[-1][2]
        key = (body["kind"], body["target_url"], body.get("input_key"))
        created = key not in self.enqueued
        self.enqueued.add(key)
        return httpx.Response(self.enqueue_status, json={"id": str(uuid.uuid4()), "created": created})

    def _task_route(self, request: httpx.Request, task_id: str, action: str) -> httpx.Response:
        body = json.loads(request.content) if request.content and action != "artifacts" else None
        self.calls.append((action, task_id, body))
        if action == "artifacts":
            self.uploads.append(request)
            if self.upload_status >= 400:
                return httpx.Response(self.upload_status, text=self.upload_detail)
            self.stored.append(artifact_json())
            return httpx.Response(self.upload_status, json=self.stored[-1])
        return httpx.Response(200, json={"id": task_id, "status": "x", "last_error": "x"})

    def _budget_route(self, request: httpx.Request) -> httpx.Response:
        if self.ledger_remaining is None:
            return httpx.Response(503, text="ledger down")
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        self.calls.append((path.rsplit("/", 1)[-1] if "/budgets/" in path else "budgets", "", body))
        if path.endswith("/budgets"):
            return httpx.Response(200, json={"items": [self._row()]})
        if path.endswith("/reserve"):
            return self._reserve(float(body["amount"]))
        if path.endswith("/adjust"):
            self.ledger_remaining -= float(body["delta"])
        if path.endswith("/exhaust"):
            self.ledger_exhausted = True
        return httpx.Response(200, json=self._row())

    def _reserve(self, amount: float) -> httpx.Response:
        assert self.ledger_remaining is not None
        if self.ledger_exhausted or self.ledger_remaining < amount:
            return httpx.Response(409, json={"granted": False, "remaining": self.ledger_remaining})
        self.ledger_remaining -= amount
        return httpx.Response(200, json={"granted": True, "remaining": self.ledger_remaining})

    def _row(self) -> dict[str, object]:
        remaining = self.ledger_remaining or 0.0
        return {
            "resource": "browser_seconds",
            "period": "2026-10-27",
            "cap": 480,
            "used": 480 - remaining,
            "remaining": remaining,
            "exhausted": self.ledger_exhausted,
        }

    def client(self, monkeypatch: pytest.MonkeyPatch) -> DiscoveryMachineClient:
        """Return a machine client whose every HTTP call lands in :meth:`handler`."""

        def factory(**kwargs: Any) -> httpx.Client:
            kwargs["transport"] = httpx.MockTransport(self.handler)
            return _REAL_HTTPX_CLIENT(**kwargs)

        monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", factory)
        return DiscoveryMachineClient(API_BASE, "test-machine-key")


def robots_fetcher(robots: str | None = None, *, robots_status: int = 404) -> PoliteUrlFetcher:
    """Return a fetcher whose only reachable URL is ``robots.txt`` (``robots_status`` unless ``robots`` has rules)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots) if robots is not None else httpx.Response(robots_status)
        return httpx.Response(500, text="the render worker must not fetch pages itself")

    http = _REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler))
    return PoliteUrlFetcher(min_interval_per_host_s=0, http_client=http)


class FakeBrowser:
    """A scripted browser: each ``render`` returns the next page or raises the next error; calls are recorded."""

    def __init__(self, *outcomes: RenderedPage | BrowserError) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[str] = []

    def render(self, url: str) -> RenderedPage:
        """Return or raise the next scripted outcome."""
        self.calls.append(url)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BrowserError):
            raise outcome
        return outcome

    def screenshot(self, url: str) -> ScreenshotImage:
        """Not used by chapter 15."""
        raise NotImplementedError


def page(html: str = "<html><body>rendered</body></html>", *, ms: int = 2000, status: int | None = 200) -> RenderedPage:
    """Return a rendered page costing ``ms`` browser milliseconds."""
    return RenderedPage(html, ms, status, "https://portal.example/final")
