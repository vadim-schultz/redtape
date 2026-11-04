"""``candidates emit`` CLI tests against a recording stand-in for the machine API (chapter 11, loop C)."""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

API_BASE = "https://redtape.test"
MACHINE = "/api/v1/discovery/machine/candidates"
FIRST, SECOND, THIRD = (uuid.UUID(int=n) for n in (1, 2, 3))
_REAL_HTTPX_CLIENT = httpx.Client


class _Api:
    """Records every call; ``skip`` maps candidate ids to the reason their emit or preview is skipped."""

    def __init__(self, *, listed: list[uuid.UUID] | None = None, skip: dict[uuid.UUID, str] | None = None) -> None:
        self.listed = listed or []
        self.skip = skip or {}
        self.calls: list[tuple[str, str]] = []
        self.queries: list[dict[str, str]] = []
        self.emitted: list[list[str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append((request.method, path))
        if request.method == "GET" and path == MACHINE + "/":
            self.queries.append(dict(request.url.params))
            return httpx.Response(200, json=self._page())
        if request.method == "GET" and path.endswith("/emit-preview"):
            return httpx.Response(200, json=self._preview(uuid.UUID(path.split("/")[-2])))
        if request.method == "POST" and path == MACHINE + "/emit":
            return self._emit(json.loads(request.content.decode())["candidate_ids"])
        return httpx.Response(404, text=f"unexpected {request.method} {path}")

    def _page(self) -> dict[str, Any]:
        items = [self._listed_item(i) for i in self.listed]
        return {"items": items, "total": len(items), "offset": 0, "limit": len(items)}

    @staticmethod
    def _listed_item(candidate_id: uuid.UUID) -> dict[str, Any]:
        title = f"Dokument {candidate_id.int}"
        return {
            "id": str(candidate_id),
            "jurisdiction_id": str(uuid.UUID(int=900)),
            "key": f"dokument-{candidate_id.int}",
            "title_i18n": {"de": title},
            "roles": ["required"],
            "mention_count": 4,
        }

    def _preview(self, candidate_id: uuid.UUID) -> dict[str, Any]:
        reason = self.skip.get(candidate_id)
        suggestion = None if reason else {"kind": "new_document", "source_url": "https://x.test", "payload": {}}
        return {"candidate_id": str(candidate_id), "suggestion": suggestion, "skip_reason": reason, "conflicts": []}

    def _emit(self, ids: list[str]) -> httpx.Response:
        self.emitted.append(ids)
        items = [self._emit_item(uuid.UUID(i)) for i in ids]
        skipped = sum(item["skip_reason"] is not None for item in items)
        replayed = sum(item["replayed"] for item in items)
        counts = {"created_count": len(items) - skipped - replayed, "skipped_count": skipped}
        return httpx.Response(200, json={"items": items, "replayed_count": replayed, **counts})

    def _emit_item(self, candidate_id: uuid.UUID) -> dict[str, Any]:
        reason = self.skip.get(candidate_id)
        replayed = reason == "replayed"
        suggestion = None if reason and not replayed else str(uuid.uuid5(uuid.NAMESPACE_URL, str(candidate_id)))
        skip_reason = None if replayed else reason
        return {
            "candidate_id": str(candidate_id),
            "suggestion_id": suggestion,
            "skip_reason": skip_reason,
            "replayed": replayed,
            "conflicts": [],
        }


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> _Api:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    fake = _Api()

    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(fake)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)
    return fake


def _emit(*args: str) -> int:
    return main(["candidates", "emit", *args])


def test_emit_dry_run_calls_only_the_preview_route(api: _Api, capsys: pytest.CaptureFixture[str]) -> None:
    api.skip = {SECOND: "duplicate"}

    code = _emit("--id", str(FIRST), "--id", str(SECOND), "--dry-run")

    assert code == 0
    assert api.calls == [("GET", f"{MACHINE}/{FIRST}/emit-preview"), ("GET", f"{MACHINE}/{SECOND}/emit-preview")]
    out = capsys.readouterr().out
    assert "would create 1" in out and "skipped 1" in out and "duplicate" in out


def test_emit_dry_run_never_posts_even_when_every_candidate_is_emittable(api: _Api) -> None:
    api.listed = [FIRST, SECOND]

    _emit("--all-staged", "--dry-run")

    assert all(method == "GET" for method, _ in api.calls)
    assert api.emitted == []


def test_emit_applies_min_mentions_and_limit_when_selecting_staged_candidates(api: _Api) -> None:
    api.listed = [FIRST, SECOND]

    code = _emit("--all-staged", "--min-mentions", "3", "--limit", "5")

    assert code == 0
    assert api.queries == [{"status": "staged", "min_mentions": "3", "limit": "5"}]
    assert api.emitted == [[str(FIRST), str(SECOND)]]


def test_emit_limit_defaults_to_ten(api: _Api) -> None:
    api.listed = [FIRST]

    _emit("--all-staged")

    assert api.queries[0]["limit"] == "10"


@pytest.mark.parametrize("limit", ["51", "0", "-1"])
def test_emit_rejects_a_limit_outside_one_to_fifty_before_any_call(api: _Api, limit: str) -> None:
    code = _emit("--all-staged", "--limit", limit)

    assert code == 2
    assert api.calls == []


def test_emit_rejects_more_ids_than_the_limit_before_any_call(api: _Api) -> None:
    code = _emit("--id", str(FIRST), "--id", str(SECOND), "--limit", "1")

    assert code == 2
    assert api.calls == []


@pytest.mark.parametrize("args", [[], ["--all-staged", "--id", str(FIRST)]])
def test_emit_needs_exactly_one_way_to_choose_candidates(api: _Api, args: list[str]) -> None:
    exit_code = _emit(*args)

    assert exit_code == 2
    assert api.calls == []


def test_emit_prints_created_replayed_and_skipped_counts_with_suggestion_ids(
    api: _Api, capsys: pytest.CaptureFixture[str]
) -> None:
    api.skip = {SECOND: "replayed", THIRD: "duplicate"}

    code = _emit("--id", str(FIRST), "--id", str(SECOND), "--id", str(THIRD))

    out = capsys.readouterr().out
    assert code == 0
    assert "created 1" in out and "replayed 1" in out and "skipped 1" in out
    assert str(uuid.uuid5(uuid.NAMESPACE_URL, str(FIRST))) in out
    assert f"{THIRD} duplicate" in out


def test_emit_with_nothing_selected_calls_no_emit_route(api: _Api, capsys: pytest.CaptureFixture[str]) -> None:
    code = _emit("--all-staged")

    assert code == 0
    assert api.emitted == []
    assert "no candidates selected" in capsys.readouterr().out


def test_emit_reports_an_api_failure_and_exits_one(
    api: _Api, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(api, "_emit", lambda ids: httpx.Response(401, text="Not authenticated"))

    code = _emit("--id", str(FIRST))

    assert code == 1
    assert "401" in capsys.readouterr().err
