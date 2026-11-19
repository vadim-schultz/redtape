"""Screenshot sweeper and post-extraction hook: only rendered pages without a screenshot are queued (chapter 8)."""

from __future__ import annotations

import uuid

import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.capture_enqueue import enqueue_screenshot_for_mentions, sweep_screenshots
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.policy import DrainPolicy

from drain_deps_for import deps_for
from render_fakes import CATALOGUE_ID, FakeApi, FakeBrowser, missing_row, robots_fetcher, task_json

URL_A = "https://portal.example/service/a"
URL_B = "https://portal.example/service/b"


def _client(api: FakeApi, monkeypatch: pytest.MonkeyPatch) -> DiscoveryIngestClient:
    return api.client(monkeypatch)


def _captures(api: FakeApi) -> list[dict[str, object]]:
    return [body for name, _, body in api.calls if name == "enqueue" and body["kind"] == "capture_screenshot"]


def _task() -> ClaimedTask:
    return ClaimedTask.model_validate(task_json(uuid.uuid4(), URL_A, "llm_extract"))


def test_the_sweeper_queues_one_capture_for_each_rendered_page_without_a_screenshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sweep · two rendered pages lacking a screenshot each get one capture_screenshot task at priority 300."""
    api = FakeApi([])
    api.missing_screenshots = [missing_row(URL_A), missing_row(URL_B)]

    queued = sweep_screenshots(_client(api, monkeypatch), limit=50)

    assert queued == 2
    assert [(body["target_url"], body["priority"], body["input_key"]) for body in _captures(api)] == [
        (URL_A, 300, "shot@1"),
        (URL_B, 300, "shot@1"),
    ]
    assert api.gap_queries == [{"limit": "50"}]


def test_the_sweeper_queues_nothing_when_every_rendered_page_has_a_screenshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """sweep · the route lists no page without a screenshot, so the sweep queues nothing and reports zero."""
    api = FakeApi([])
    api.missing_screenshots = []

    assert sweep_screenshots(_client(api, monkeypatch), limit=50) == 0
    assert _captures(api) == []


def test_the_sweep_is_bounded_by_its_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """sweep · five pages lacking a screenshot and a limit of two: the read asks for two and two are queued."""
    api = FakeApi([])
    api.missing_screenshots = [missing_row(f"https://portal.example/service/{n}") for n in range(5)]

    queued = sweep_screenshots(_client(api, monkeypatch), limit=2)

    assert queued == 2 and api.gap_queries == [{"limit": "2"}]
    assert len(_captures(api)) == 2


def test_a_refused_sweep_read_queues_nothing_and_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """sweep · a refused read is logged and counts zero; the drain that runs the sweep is not stopped."""
    api = FakeApi([])
    api.missing_status = 500

    assert sweep_screenshots(_client(api, monkeypatch), limit=50) == 0
    assert _captures(api) == []


def test_the_hook_queues_a_capture_for_a_page_that_lacks_a_screenshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """hook · after extraction a page with no screenshot gets one capture_screenshot task for its url."""
    api = FakeApi([])
    task = _task()

    assert enqueue_screenshot_for_mentions(_client(api, monkeypatch), task) is True
    assert [body["target_url"] for body in _captures(api)] == [URL_A]


def test_the_hook_is_a_no_op_when_the_page_already_has_a_screenshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """hook · a page whose screenshot exists is skipped: no enqueue, and the hook still reports success."""
    api = FakeApi([])
    api.missing_screenshots = []

    assert enqueue_screenshot_for_mentions(_client(api, monkeypatch), _task()) is True
    assert _captures(api) == [] and api.gap_queries == [{"catalogue_service_id": str(CATALOGUE_ID), "limit": "1"}]


def _drain(monkeypatch: pytest.MonkeyPatch, api: FakeApi, kinds: tuple[str, ...], limit: int | None) -> None:
    policy = DrainPolicy(max_tasks=5, kinds=kinds, browser_budget_seconds=480.0)
    deps = deps_for(api.client(monkeypatch), robots_fetcher(), browser=FakeBrowser(), screenshot_sweep_limit=limit)
    run_worker_drain(deps, policy)


def test_a_capture_drain_sweeps_rendered_pages_before_it_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    """drain · a drain that claims capture_screenshot queues a capture for each rendered page that lacks one."""
    api = FakeApi([[]])
    api.missing_screenshots = [missing_row(URL_A)]

    _drain(monkeypatch, api, ("capture_screenshot",), limit=50)

    assert [body["target_url"] for body in _captures(api)] == [URL_A]


def test_a_render_only_drain_and_a_drain_without_a_limit_do_not_sweep(monkeypatch: pytest.MonkeyPatch) -> None:
    """drain · only a drain that claims capture_screenshot sweeps, and only with a limit; neither other case reads the route."""
    render_only = FakeApi([[]])
    _drain(monkeypatch, render_only, ("render_page",), limit=50)
    no_limit = FakeApi([[]])
    _drain(monkeypatch, no_limit, ("capture_screenshot",), limit=None)

    assert render_only.gap_queries == [] and no_limit.gap_queries == []
