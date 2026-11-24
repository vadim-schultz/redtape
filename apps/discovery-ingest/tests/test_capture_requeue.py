"""``capture requeue``: queue capture_screenshot for the categorised pages that lack a screenshot (chapter 1)."""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.capture_enqueue import (
    CAPTURE_INPUT_KEY,
    CAPTURE_PRIORITY,
    capture_request,
    enqueue_screenshot_for_mentions,
)
from pydantic import SecretStr

from render_fakes import missing_row

API_BASE = "https://redtape.test"
API_KEY = "test-machine-key"
_REAL_HTTPX_CLIENT = httpx.Client


def _source(n: int) -> dict[str, object]:
    return {
        "catalogue_service_id": str(uuid.UUID(int=n + 1000)),
        "source_url": f"https://portal.example/page/{n}",
        "host": "portal.example",
        "has_screenshot": False,
        "mention_count": 3,
    }


class Api:
    """Serves the sources list (paged) and the enqueue route; records every request."""

    def __init__(self, sources: list[dict[str, object]]) -> None:
        self.sources = sources
        self.requests: list[httpx.Request] = []
        self.known: set[tuple[str, str, str | None]] = set()
        self.refused_urls: set[str] = set()
        self.list_status = 200
        self.gaps: list[dict[str, object]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/candidates/sources"):
            return self._list(request)
        if request.method == "POST" and request.url.path.endswith("/machine/tasks"):
            return self._enqueue(request)
        if request.method == "GET" and request.url.path.endswith("/artifacts/missing-screenshot"):
            return httpx.Response(200, json={"items": self.gaps})
        return httpx.Response(500, text="no stub")

    def _list(self, request: httpx.Request) -> httpx.Response:
        if self.list_status >= 400:
            return httpx.Response(self.list_status, text="refused")
        offset, limit = int(request.url.params["offset"]), int(request.url.params["limit"])
        items = self.sources[offset : offset + limit]
        return httpx.Response(200, json={"items": items, "total": len(self.sources), "offset": offset, "limit": limit})

    def _enqueue(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["target_url"] in self.refused_urls:
            return httpx.Response(503, text=f"unavailable for {API_KEY}")
        identity = (body["catalogue_service_id"], body["target_url"], body.get("input_key"))
        created = identity not in self.known
        self.known.add(identity)
        return httpx.Response(201 if created else 200, json={"id": str(uuid.uuid4()), "created": created})

    @property
    def enqueues(self) -> list[dict[str, Any]]:
        """The bodies of the enqueue requests, in order."""
        return [json.loads(r.content) for r in self.requests if r.method == "POST"]

    @property
    def lists(self) -> list[httpx.Request]:
        """The list requests, in order."""
        return [r for r in self.requests if r.method == "GET"]


def _install(monkeypatch: pytest.MonkeyPatch, fake: Api) -> Api:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", API_KEY)

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(fake.handler)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
    return fake


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Api:
    """An API whose sources route lists two pages without a screenshot."""
    return _install(monkeypatch, Api([_source(1), _source(2)]))


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(["capture", "requeue", *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_capture_requeue_enqueues_one_capture_per_source_row(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """capture requeue · two rows give two capture_screenshot tasks for the row's url with the shared key."""
    code, out, _ = _run(capsys, "--host", "portal.example")

    assert code == 0 and out.split() == ["pages=2", "queued=2", "already_queued=0", "failed=0"]
    assert [(b["kind"], b["priority"], b["input_key"], b["target_url"]) for b in api.enqueues] == [
        ("capture_screenshot", 300, "shot@1", "https://portal.example/page/1"),
        ("capture_screenshot", 300, "shot@1", "https://portal.example/page/2"),
    ]
    assert dict(api.lists[0].url.params) == {
        "missing": "screenshot",
        "host": "portal.example",
        "offset": "0",
        "limit": "50",
    }


def test_capture_requeue_counts_a_known_key_as_already_queued(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """capture requeue · a second run is answered created=false: already_queued, nothing new, exit 0."""
    _run(capsys)
    code, out, _ = _run(capsys)

    assert code == 0 and "pages=2 queued=0 already_queued=2 failed=0" in out


def test_capture_requeue_dry_run_makes_no_enqueue_call(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """capture requeue · --dry-run reports the pages with dry_run=true and sends only the list call."""
    code, out, _ = _run(capsys, "--dry-run")

    assert code == 0 and out.split() == ["pages=2", "queued=0", "already_queued=0", "failed=0", "dry_run=true"]
    assert api.enqueues == [] and len(api.lists) == 1


def test_capture_requeue_stops_at_the_limit_across_pages(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """capture requeue · 150 rows over two list pages with --limit 120 give exactly 120 enqueue calls."""
    fake = _install(monkeypatch, Api([_source(n) for n in range(150)]))

    code, out, _ = _run(capsys, "--limit", "120")

    assert code == 0 and "pages=120 queued=120" in out
    assert len(fake.enqueues) == 120 and len(fake.lists) == 2
    assert len({b["target_url"] for b in fake.enqueues}) == 120


def test_capture_requeue_reports_failures_and_exits_1_but_tries_the_rest(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    """capture requeue · a refused enqueue counts failed=1, exits 1, leaks nothing, and the other page is queued."""
    api.refused_urls.add("https://portal.example/page/1")

    code, out, err = _run(capsys)

    assert code == 1 and "pages=2 queued=1 already_queued=0 failed=1" in out
    assert len(api.enqueues) == 2
    assert API_KEY not in out + err and "portal.example" not in out + err


def test_capture_requeue_exits_1_when_the_sources_route_refuses(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """capture requeue · a refused list call is an API error: exit 1, a message on stderr, no enqueue."""
    api.list_status = 401

    code, out, err = _run(capsys)

    assert code == 1 and out == "" and "capture requeue command failed" in err and api.enqueues == []


@pytest.mark.parametrize("limit", ["0", "201", "many"])
def test_capture_requeue_rejects_a_bad_limit_before_any_call(
    api: Api, capsys: pytest.CaptureFixture[str], limit: str
) -> None:
    """capture requeue · 0, 201 and text are an argparse error (exit 2) with no request made."""
    exit_code = main(["capture", "requeue", "--limit", limit])

    assert exit_code == 2 and api.requests == []
    capsys.readouterr()


def test_capture_requeue_passes_chosen_service_ids_and_refuses_more_than_twenty(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    """capture requeue · --service-id is sent as repeated catalogue_service_id; 21 ids are refused before any call."""
    ids = [str(uuid.UUID(int=n)) for n in range(1, 4)]
    flags = [part for value in ids for part in ("--service-id", value)]

    _run(capsys, *flags)
    exit_code = main(
        ["capture", "requeue", *[p for n in range(21) for p in ("--service-id", str(uuid.UUID(int=n + 1)))]]
    )

    assert api.lists[0].url.params.get_list("catalogue_service_id") == ids
    assert exit_code == 2 and len(api.lists) == 1
    capsys.readouterr()


def test_capture_request_is_shared_with_the_extraction_hook(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    """capture_request · the extraction hook posts exactly the request ``capture_request`` builds."""
    from discovery_ingest.client import DiscoveryIngestClient

    row, url = uuid.UUID(int=7), "https://portal.example/page/7"
    task = ClaimedTask.model_validate(
        {
            "id": str(uuid.uuid4()),
            "catalogue_service_id": str(row),
            "kind": "extract_page",
            "target_url": url,
            "status": "claimed",
            "priority": 100,
            "lease_expires_at": "2026-10-30T12:00:00Z",
        }
    )

    api.gaps = [missing_row(url, row)]

    assert enqueue_screenshot_for_mentions(DiscoveryIngestClient(API_BASE, SecretStr(API_KEY)), task) is True

    request = capture_request(row, url)
    assert api.enqueues == [request.model_dump(mode="json", exclude_none=True)]
    assert (request.priority, request.input_key) == (CAPTURE_PRIORITY, CAPTURE_INPUT_KEY) == (300, "shot@1")
