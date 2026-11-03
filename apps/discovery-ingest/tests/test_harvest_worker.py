"""Worker harvest_payload handler tests (chapter 7, loop C)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.harvest import handle_harvest_payload
from pydantic import SecretStr

API_BASE = "https://redtape.test"
TASK_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CATALOGUE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
MACHINE = "/api/v1/discovery/machine"
_REAL_HTTPX_CLIENT = httpx.Client


class _Api:
    """A recording stand-in for the machine API; ``mentions`` and ``catalogue`` choose the replies."""

    def __init__(self, *, payload: dict[str, object], catalogue_status: int = 200, mentions_status: int = 200) -> None:
        self.payload = payload
        self.catalogue_status = catalogue_status
        self.mentions_status = mentions_status
        self.mention_batches: list[list[dict[str, Any]]] = []
        self.fails: list[dict[str, Any]] = []
        self.completes = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == f"{MACHINE}/catalogue/{CATALOGUE_ID}":
            return self._catalogue()
        if path.endswith("/candidates/mentions"):
            return self._mentions(json.loads(request.content.decode())["items"])
        if path.endswith("/fail"):
            self.fails.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"id": str(TASK_ID), "status": "failed", "last_error": "x"})
        if path.endswith("/complete"):
            self.completes += 1
            return httpx.Response(200, json={"id": str(TASK_ID), "status": "completed"})
        return httpx.Response(404, text=f"unexpected {path}")

    def _catalogue(self) -> httpx.Response:
        if self.catalogue_status != 200:
            return httpx.Response(self.catalogue_status, text="catalogue problem")
        body = {
            "id": str(CATALOGUE_ID),
            "source": "pvog",
            "portal_url": None,
            "title_i18n": {"de": "Leistung"},
            "raw_payload": self.payload,
        }
        return httpx.Response(200, json=body)

    def _mentions(self, items: list[dict[str, Any]]) -> httpx.Response:
        if self.mentions_status != 200:
            return httpx.Response(self.mentions_status, text="mentions problem")
        self.mention_batches.append(items)
        counts = {"candidates_created": len(items), "mentions_created": len(items), "mentions_updated": 0}
        return httpx.Response(200, json=counts)


def _run(monkeypatch: pytest.MonkeyPatch, api: Callable[[httpx.Request], httpx.Response]) -> str:
    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(api)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)
    task = ClaimedTask(
        id=TASK_ID,
        catalogue_service_id=CATALOGUE_ID,
        kind="harvest_payload",
        target_url="https://pvog.example.de/leistung/1",
        status="claimed",
        priority=50,
        lease_expires_at=datetime.now(UTC),
    )
    client = DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))
    return handle_harvest_payload(task, client=client, fetcher=PoliteUrlFetcher(min_interval_per_host_s=0))


def _documents_payload(count: int) -> dict[str, object]:
    items = "".join(f"<li>Dokument {number:03d}</li>" for number in range(count))
    return {"details": [{"code": "08", "text": f"<ul>{items}</ul>", "links": [], "filled": True}]}


def test_harvest_handler_posts_mentions_in_chunks_and_completes_the_task(monkeypatch: pytest.MonkeyPatch) -> None:
    """harvest handler · posts mentions in chunks and completes the task."""
    api = _Api(payload=_documents_payload(120))

    outcome = _run(monkeypatch, api)

    assert outcome == "completed"
    assert [len(batch) for batch in api.mention_batches] == [100, 20]
    first = api.mention_batches[0][0]
    assert first["catalogue_service_id"] == str(CATALOGUE_ID)
    assert (first["role"], first["extractor"], first["source_field"]) == (
        "required",
        "pvog-payload",
        "details[code=08]",
    )
    assert (api.completes, api.fails) == (1, [])


def test_harvest_handler_completes_without_posting_when_the_payload_yields_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """harvest handler · completes without posting when the payload yields nothing."""
    api = _Api(payload={"details": []})

    assert _run(monkeypatch, api) == "completed"
    assert (api.mention_batches, api.completes, api.fails) == ([], 1, [])


def test_harvest_handler_fails_a_missing_catalogue_row_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """harvest handler · fails a missing catalogue row without retry."""
    api = _Api(payload={}, catalogue_status=404)

    assert _run(monkeypatch, api) == "failed"
    assert [fail["retryable"] for fail in api.fails] == [False]
    assert (api.mention_batches, api.completes) == ([], 0)


@pytest.mark.parametrize(
    ("catalogue_status", "mentions_status", "retryable"),
    [(503, 200, True), (200, 502, True), (200, 422, False)],
    ids=["catalogue_5xx", "mentions_5xx", "mentions_4xx"],
)
def test_harvest_handler_retries_only_api_server_errors(
    monkeypatch: pytest.MonkeyPatch, catalogue_status: int, mentions_status: int, retryable: bool
) -> None:
    """harvest handler · retries only API server errors."""
    api = _Api(payload=_documents_payload(3), catalogue_status=catalogue_status, mentions_status=mentions_status)

    assert _run(monkeypatch, api) == "failed"
    assert [fail["retryable"] for fail in api.fails] == [retryable]
    assert api.completes == 0
