"""Harvest drain · one crosswalk fetch serves every harvest task of a drain; an unusable crosswalk writes no mention."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.run import run_recorded_drain
from pydantic import SecretStr

from crosswalk_fakes import VOCABULARY
from drain_deps_for import deps_for
from run_stub import run_response

API_BASE = "https://redtape.test"
MACHINE = "/api/v1/discovery/machine"
CATALOGUE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_REAL_HTTPX_CLIENT = httpx.Client
HARVEST_ONLY = DrainPolicy(max_tasks=5, kinds=("harvest_payload",))


def _task(task_id: uuid.UUID) -> dict[str, object]:
    return {
        "id": str(task_id),
        "catalogue_service_id": str(CATALOGUE_ID),
        "kind": "harvest_payload",
        "target_url": "https://pvog.example.de/leistung/1",
        "status": "claimed",
        "priority": 50,
        "lease_expires_at": datetime.now(UTC).isoformat(),
    }


def _catalogue() -> dict[str, object]:
    details = [{"code": "08", "text": "<ul><li>Dokument 001</li></ul>", "links": [], "filled": True}]
    return {
        "id": str(CATALOGUE_ID),
        "source": "pvog",
        "portal_url": None,
        "title_i18n": {"de": "Leistung"},
        "raw_payload": {"details": details},
    }


def _unserved_leaf(body: dict[str, Any]) -> dict[str, Any]:
    """Return the served vocabulary with the PVOG leaf 1180100 naming a category the vocabulary does not serve."""
    leaves = body["crosswalk"]["pvog_leaf_mappings"]
    next(leaf for leaf in leaves if leaf["leaf_code"] == "1180100")["category_codes"] = ["not-served"]
    return body


class _Machine:
    """A recording machine API for one harvest drain: its tasks, its taxonomy reply and every settlement."""

    def __init__(self, tasks: list[uuid.UUID], taxonomy: Callable[[], httpx.Response]) -> None:
        self._pending = [_task(task_id) for task_id in tasks]
        self._taxonomy = taxonomy
        self.taxonomy_calls = 0
        self.mention_posts = 0
        self.completes = 0
        self.releases = 0
        self.finishes: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        stub = run_response(request, self.finishes)
        if stub is not None:
            return stub
        path = request.url.path
        if path.endswith("/taxonomy"):
            self.taxonomy_calls += 1
            return self._taxonomy()
        if path.endswith("/tasks/claim"):
            items, self._pending = self._pending, []
            return httpx.Response(200, json={"items": items})
        if path.endswith(f"/catalogue/{CATALOGUE_ID}"):
            return httpx.Response(200, json=_catalogue())
        return self._settle(path)

    def _settle(self, path: str) -> httpx.Response:
        if path.endswith("/candidates/mentions"):
            self.mention_posts += 1
            return httpx.Response(200, json={"candidates_created": 1, "mentions_created": 1, "mentions_updated": 0})
        if path.endswith("/complete"):
            self.completes += 1
            return httpx.Response(200, json={"id": str(uuid.uuid4()), "status": "completed"})
        if path.endswith("/release"):
            self.releases += 1
            return httpx.Response(200, json={"id": str(uuid.uuid4()), "status": "pending"})
        return httpx.Response(500, text=f"unexpected {path}")


def _patch_transport(monkeypatch: pytest.MonkeyPatch, machine: _Machine) -> None:
    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(machine)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)


def _drain(monkeypatch: pytest.MonkeyPatch, machine: _Machine, policy: DrainPolicy = HARVEST_ONLY) -> DrainReport:
    _patch_transport(monkeypatch, machine)
    client = DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))
    return run_recorded_drain(deps_for(client, PoliteUrlFetcher(min_interval_per_host_s=0)), policy)


def _served(body: dict[str, Any]) -> Callable[[], httpx.Response]:
    return lambda: httpx.Response(200, json=body)


def test_one_drain_fetches_the_crosswalk_once_for_all_its_harvest_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    """harvest drain · two harvest tasks in one drain share one taxonomy fetch and both complete."""
    machine = _Machine([uuid.uuid4(), uuid.uuid4()], _served(VOCABULARY))

    report = _drain(monkeypatch, machine)

    assert (machine.taxonomy_calls, machine.mention_posts, machine.completes) == (1, 2, 2)
    assert (report.completed, report.succeeded, report.stop_reason) == (2, True, "batch_limit")
    assert machine.finishes[-1]["status"] == "succeeded"


def test_a_drain_without_harvest_tasks_never_asks_for_the_crosswalk(monkeypatch: pytest.MonkeyPatch) -> None:
    """harvest drain · a drain that claims no harvest task makes no taxonomy call."""
    machine = _Machine([], _served(VOCABULARY))

    report = _drain(monkeypatch, machine, DrainPolicy(max_tasks=5, kinds=("fetch_url",)))

    assert (machine.taxonomy_calls, machine.mention_posts) == (0, 0)
    assert report.succeeded is True


def test_an_unreachable_taxonomy_stops_the_drain_before_any_mention_is_written(monkeypatch: pytest.MonkeyPatch) -> None:
    """harvest drain · an unreachable taxonomy fails the run, writes no mention and returns the claimed task."""

    def unreachable() -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    machine = _Machine([uuid.uuid4()], unreachable)

    report = _drain(monkeypatch, machine)

    assert (report.succeeded, report.stop_reason) == (False, "error")
    assert report.error is not None and "machine taxonomy unavailable" in report.error
    assert (machine.mention_posts, machine.completes, machine.releases) == (0, 0, 1)
    assert machine.finishes[-1]["status"] == "failed"


def test_an_invalid_taxonomy_stops_the_drain_before_any_mention_is_written(monkeypatch: pytest.MonkeyPatch) -> None:
    """harvest drain · a crosswalk that names an unserved category fails the run, writes no mention and returns the task."""
    machine = _Machine([uuid.uuid4()], _served(_unserved_leaf(json.loads(json.dumps(VOCABULARY)))))

    report = _drain(monkeypatch, machine)

    assert (report.succeeded, report.stop_reason) == (False, "error")
    assert report.error is not None and "not-served" in report.error
    assert (machine.mention_posts, machine.completes, machine.releases) == (0, 0, 1)
    assert machine.finishes[-1]["status"] == "failed"
