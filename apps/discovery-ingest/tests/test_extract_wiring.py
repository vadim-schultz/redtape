"""The after_snapshot hook queues extract_page only when an extractor matches (chapter 17, Loop C)."""

from __future__ import annotations

import json
import uuid

import pytest
from discovery_ingest.cli import main
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.policy import DrainPolicy

from extract_fakes import ExtractApi, FakeExtractor, extract_task
from render_fakes import FakeApi, FakeBrowser, page, robots_fetcher, task_json

URL = "https://portal.example/service/1"


def _render(monkeypatch: pytest.MonkeyPatch, api: FakeApi, *extractors: FakeExtractor, tasks: int = 1) -> DrainReport:
    api.batches = [[task_json(uuid.uuid4(), URL) for _ in range(tasks)]]
    browser = FakeBrowser(*[page() for _ in range(tasks)])
    policy = DrainPolicy(max_tasks=5, kinds=("render_page",), browser_budget_seconds=480.0)
    client = api.client(monkeypatch)
    return run_worker_drain(client, robots_fetcher(), policy, browser=browser, extractors=extractors)


def _enqueues(api: FakeApi) -> list[dict[str, object]]:
    return [body for name, _, body in api.calls if name == "enqueue"]


def test_after_snapshot_enqueues_extract_page_with_the_artifact_id_and_extractor_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """after_snapshot · a matching extractor earns one extract_page task for the stored snapshot at priority 100."""
    api = FakeApi([])

    _render(monkeypatch, api, FakeExtractor("verwaltung-bund", "2"))

    assert _enqueues(api) == [
        {
            "catalogue_service_id": str(api.stored[0]["catalogue_service_id"]),
            "kind": "extract_page",
            "target_url": URL,
            "priority": 100,
            "input_key": "verwaltung-bund@2",
            "artifact_id": api.stored[0]["id"],
        }
    ]


def test_after_snapshot_enqueues_nothing_when_no_extractor_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """after_snapshot · an empty registry (production) or a registry with no match creates no task."""
    api = FakeApi([])

    _render(monkeypatch, api)
    _render(monkeypatch, api, FakeExtractor(host="elsewhere.example"))

    assert _enqueues(api) == []


def test_a_failed_enqueue_never_fails_the_render(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """after_snapshot · an API error on the extract enqueue is logged; the render task still completes."""
    api = FakeApi([])
    api.enqueue_status = 500

    report = _render(monkeypatch, api, FakeExtractor())

    assert (report.completed, report.failed) == (1, 0)
    assert "extract enqueue failed" in capsys.readouterr().err


def test_a_new_extractor_version_enqueues_a_second_task_and_the_same_version_does_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """after_snapshot · the input key carries the version, so only a bump creates another task for the snapshot."""
    api = FakeApi([])

    _render(monkeypatch, api, FakeExtractor("fake", "1"), tasks=2)
    created_by_v1 = len(api.enqueued)
    _render(monkeypatch, api, FakeExtractor("fake", "2"))

    assert [body["input_key"] for body in _enqueues(api)] == ["fake@1", "fake@1", "fake@2"]
    assert (created_by_v1, len(api.enqueued)) == (1, 2)


def test_the_worker_sends_the_note_when_completing_with_no_extractor_through_the_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · with the empty production registry an extract_page task completes with note no_extractor."""
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    api = ExtractApi([extract_task()])
    api.client(monkeypatch)

    assert main(["worker", "drain", "--kinds", "extract_page"]) == 0

    assert [body for _, body in api.named("complete")] == [{"note": "no_extractor"}]
    assert json.loads(capsys.readouterr().out)["completed"] == 1
