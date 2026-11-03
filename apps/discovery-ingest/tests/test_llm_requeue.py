"""``llm requeue``: queue llm_extract for the latest snapshot of each catalogue row (chapter E7, Loop B)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.worker.llm_enqueue import llm_input_key

API_BASE = "https://redtape.test"
API_KEY = "test-machine-key"
MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
_REAL_HTTPX_CLIENT = httpx.Client
ROWS = [uuid.UUID(int=n + 100) for n in range(4)]


def _artifact(index: int, row: uuid.UUID) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid.UUID(int=index)),
        "catalogue_service_id": str(row),
        "discovery_task_id": None,
        "kind": "html_snapshot",
        "storage_key": f"k{index}",
        "sha256": "abc",
        "content_type": "text/html",
        "byte_size": 100,
        "source_url": f"https://portal.example/page/{row.int}",
        "final_url": None,
        "fetched_at": now,
        "created_at": now,
    }


class Api:
    """Serves the artifact list (newest first, paged) and the enqueue route; records every request."""

    def __init__(self, artifacts: list[dict[str, object]]) -> None:
        self.artifacts = artifacts
        self.requests: list[httpx.Request] = []
        self.known: set[tuple[str, str | None]] = set()
        self.enqueue_status = 201

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/artifacts"):
            return self._list(request)
        if request.method == "POST" and request.url.path.endswith("/machine/tasks"):
            return self._enqueue(request)
        return httpx.Response(500, text="no stub")

    def _list(self, request: httpx.Request) -> httpx.Response:
        offset, limit = int(request.url.params["offset"]), int(request.url.params["limit"])
        items = self.artifacts[offset : offset + limit]
        return httpx.Response(
            200, json={"items": items, "total": len(self.artifacts), "offset": offset, "limit": limit}
        )

    def _enqueue(self, request: httpx.Request) -> httpx.Response:
        if self.enqueue_status >= 400:
            return httpx.Response(self.enqueue_status, text=f"refused for key {API_KEY}")
        body = json.loads(request.content)
        identity = (body["target_url"], body.get("input_key"))
        created = identity not in self.known
        self.known.add(identity)
        return httpx.Response(201, json={"id": str(uuid.uuid4()), "created": created})

    @property
    def enqueues(self) -> list[dict[str, Any]]:
        """The bodies of the enqueue requests, in order."""
        return [json.loads(r.content) for r in self.requests if r.method == "POST"]


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Api:
    """An API with snapshots for four rows (the first row has a newer and an older one)."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", API_KEY)
    monkeypatch.setenv("LLM_MODEL", MODEL)
    fake = Api([_artifact(1, ROWS[0]), _artifact(2, ROWS[1]), _artifact(3, ROWS[0]), _artifact(4, ROWS[2])])

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(fake.handler)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
    return fake


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = main(["llm", "requeue", *argv])
    return code, capsys.readouterr().out


def _run_with_stderr(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(["llm", "requeue", *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_requeue_enqueues_one_task_per_latest_snapshot_with_the_current_key(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    """llm requeue · three rows, one task each for the newest snapshot (artifact 1 over 3), the versioned key."""
    code, out = _run(capsys, "--host", "portal.example")

    assert code == 0 and "pages=3 queued=3 already_queued=0 failed=0" in out
    assert [(b["artifact_id"], b["kind"], b["priority"]) for b in api.enqueues] == [
        (str(uuid.UUID(int=1)), "llm_extract", 200),
        (str(uuid.UUID(int=2)), "llm_extract", 200),
        (str(uuid.UUID(int=4)), "llm_extract", 200),
    ]
    assert {b["input_key"] for b in api.enqueues} == {llm_input_key(MODEL)}
    assert api.requests[0].url.params["host"] == "portal.example"


def test_requeue_skips_pages_with_the_current_key_and_enqueues_again_after_a_version_bump(
    api: Api, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """llm requeue · a second run queues nothing; a new prompt version queues every page once more."""
    _run(capsys)
    _, again = _run(capsys)
    monkeypatch.setattr("discovery_ingest.worker.llm_enqueue.PROMPT_VERSION", "ext-next")
    _, bumped = _run(capsys)

    assert "queued=0 already_queued=3" in again
    assert "queued=3 already_queued=0" in bumped
    assert len({b["input_key"] for b in api.enqueues}) == 2


def test_requeue_limit_bounds_the_pages_and_defaults_to_fifty(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """llm requeue · --limit 2 queues two pages; with no flag all three (under the default of 50) are queued."""
    _, limited = _run(capsys, "--limit", "2")
    _, everything = _run(capsys)

    assert "pages=2 queued=2" in limited and "pages=3 queued=1 already_queued=2" in everything


def test_requeue_dry_run_makes_no_enqueue_call(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """llm requeue · --dry-run lists the pages and reports them without a single POST."""
    code, out = _run(capsys, "--dry-run")

    assert code == 0 and "pages=3 queued=0" in out and "dry_run=true" in out
    assert api.enqueues == []


@pytest.mark.parametrize("limit", ["201", "0", "many"])
def test_requeue_rejects_a_limit_over_200_or_not_positive_before_any_call(
    api: Api, capsys: pytest.CaptureFixture[str], limit: str
) -> None:
    """llm requeue · 201, 0 and text are refused (exit 2) with no request made."""
    with pytest.raises(SystemExit) as stop:
        main(["llm", "requeue", "--limit", limit])

    assert stop.value.code == 2 and api.requests == []
    capsys.readouterr()


def test_requeue_without_a_model_exits_2_before_any_call(
    api: Api, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """llm requeue · the key is derived from the model, so no LLM_MODEL means no call."""
    monkeypatch.setenv("LLM_MODEL", "")

    code, _, err = _run_with_stderr(capsys)

    assert code == 2 and "LLM_MODEL" in err and api.requests == []


def test_requeue_prints_counts_only_and_never_the_key_or_a_url(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    """llm requeue · stdout is the key and four counts; a refused enqueue exits 1 and leaks neither detail nor token."""
    _, out = _run(capsys)
    api.enqueue_status = 500
    api.known.clear()
    code, failed, err = _run_with_stderr(capsys)

    assert out.split() == ["key=" + llm_input_key(MODEL), "pages=3", "queued=3", "already_queued=0", "failed=0"]
    assert code == 1 and "failed=3" in failed
    assert API_KEY not in out + failed + err and "portal.example" not in out + failed + err
