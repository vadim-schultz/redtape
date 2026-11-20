"""``llm requeue --stale-only``: re-pend the completed extractions made under an older key, under the current key (chapter 5, loop D)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.worker.llm_enqueue import llm_input_key

API_BASE = "https://redtape.test"
API_KEY = "test-machine-key"
MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
_REAL_HTTPX_CLIENT = httpx.Client
ROUTE = "/machine/tasks/requeue-superseded"


class SupersededApi:
    """Answers the superseded-requeue route with a fixed count and records each request body."""

    def __init__(self, *, matched: int, requeued: int, status: int = 200) -> None:
        self.matched = matched
        self.requeued = requeued
        self.status = status
        self.bodies: list[dict[str, Any]] = []
        self.paths: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Serve the route; any other path is a test bug and answers 500."""
        self.paths.append(request.url.path)
        if request.method == "POST" and request.url.path.endswith(ROUTE):
            self.bodies.append(json.loads(request.content))
            if self.status >= 400:
                return httpx.Response(self.status, text="requeue refused")
            return httpx.Response(200, json={"matched": self.matched, "requeued": self.requeued})
        return httpx.Response(500, text="no stub")


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> SupersededApi:
    """A stale-only requeue whose API matches two pages and queues both."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", API_KEY)
    monkeypatch.setenv("LLM_MODEL", MODEL)
    fake = SupersededApi(matched=2, requeued=2)

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(fake.handler)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
    return fake


def test_stale_only_asks_the_api_to_requeue_under_the_current_key_and_reports_the_count(
    api: SupersededApi, capsys: pytest.CaptureFixture[str]
) -> None:
    """llm requeue --stale-only · happy: the body names llm_extract, the current key and the limit; two matched and requeued."""
    code = main(["llm", "requeue", "--stale-only", "--limit", "20"])

    assert code == 0
    assert api.bodies == [{"kind": "llm_extract", "input_key": llm_input_key(MODEL), "limit": 20, "dry_run": False}]
    assert f"key={llm_input_key(MODEL)} matched=2 requeued=2 dry_run=false" in capsys.readouterr().out


def test_stale_only_refuses_a_host_filter_before_any_request(
    api: SupersededApi, capsys: pytest.CaptureFixture[str]
) -> None:
    """llm requeue --stale-only · negative: --host does not combine with --stale-only; exit 2 and no API call."""
    code = main(["llm", "requeue", "--stale-only", "--host", "portal.example"])

    assert code == 2
    assert api.paths == [] and "--host" in capsys.readouterr().err


def test_a_refused_stale_only_requeue_exits_1_without_printing_the_api_key(
    api: SupersededApi, capsys: pytest.CaptureFixture[str]
) -> None:
    """llm requeue --stale-only · negative: an API refusal is a failed run (exit 1), and the machine key is never printed."""
    api.status = 500

    code = main(["llm", "requeue", "--stale-only"])

    captured = capsys.readouterr()
    assert code == 1
    assert API_KEY not in captured.out + captured.err


def test_a_dry_run_asks_for_the_count_only(api: SupersededApi, capsys: pytest.CaptureFixture[str]) -> None:
    """llm requeue --stale-only --dry-run · the body carries dry_run true, and the report says so."""
    api.requeued = 0

    code = main(["llm", "requeue", "--stale-only", "--dry-run"])

    assert code == 0
    assert api.bodies[0]["dry_run"] is True
    assert "matched=2 requeued=0 dry_run=true" in capsys.readouterr().out
