"""Wiring: render enqueues llm_extract behind a switch and llm_extract queues a screenshot (chapter E7, Loop A)."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest
from discovery_ingest.cli import main
from discovery_ingest.extract.clean import CLEAN_VERSION
from discovery_ingest.extract.llm.prompt import PROMPT_VERSION
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.llm_enqueue import LlmEnqueuer, llm_input_key
from discovery_ingest.worker.policy import DrainPolicy

from llm_transport import ACCOUNT_ID, TOKEN, success
from llm_worker_fakes import MODEL, SERVICE, LlmApi, answer, llm_task
from render_fakes import FakeApi, FakeBrowser, page, robots_fetcher, task_json

URL = "https://portal.example/service/1"
OTHER_MODEL = "@cf/meta/llama-3.1-8b-instruct"
RENDER = ["worker", "drain", "--kinds", "render_page"]
EXTRACT = ["worker", "drain", "--kinds", "llm_extract", "--neuron-budget", "800"]


def _render(
    monkeypatch: pytest.MonkeyPatch, api: FakeApi, *, enqueue: bool, model: str = MODEL, tasks: int = 1
) -> DrainReport:
    api.batches = [[task_json(uuid.uuid4(), URL) for _ in range(tasks)]]
    client = api.client(monkeypatch)
    policy = DrainPolicy(max_tasks=5, kinds=("render_page",), browser_budget_seconds=480.0)
    browser = FakeBrowser(*[page() for _ in range(tasks)])
    hook = LlmEnqueuer(client, model) if enqueue else None
    return run_worker_drain(client, robots_fetcher(), policy, browser=browser, extractors=(), llm_enqueue=hook)


def _enqueues(api: FakeApi) -> list[dict[str, object]]:
    return [body for name, _, body in api.calls if name == "enqueue"]


def test_the_key_hashes_the_model_the_prompt_version_and_the_clean_version() -> None:
    """llm_input_key · llm: plus eight hex digits of model | prompt version | clean version; any of them changes it."""
    digest = hashlib.sha256(f"{MODEL}|{PROMPT_VERSION}|{CLEAN_VERSION}".encode()).hexdigest()[:8]

    assert llm_input_key(MODEL) == f"llm:{digest}"
    assert llm_input_key(MODEL) != llm_input_key(OTHER_MODEL)


def test_after_snapshot_enqueues_llm_extract_with_the_artifact_id_and_a_versioned_key_when_the_switch_is_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """after_snapshot · one llm_extract task at priority 200 for the stored snapshot; none when the switch is off."""
    on, off = FakeApi([]), FakeApi([])

    _render(monkeypatch, on, enqueue=True)
    _render(monkeypatch, off, enqueue=False)

    assert _enqueues(on) == [
        {
            "catalogue_service_id": str(on.stored[0]["catalogue_service_id"]),
            "kind": "llm_extract",
            "target_url": URL,
            "priority": 200,
            "input_key": llm_input_key(MODEL),
            "artifact_id": on.stored[0]["id"],
        }
    ]
    assert _enqueues(off) == []


def test_the_same_version_does_not_create_a_second_task_and_a_bumped_prompt_version_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """after_snapshot · the key carries the versions, so only a bump (prompt, cleaner or model) opens another task."""
    api = FakeApi([])

    _render(monkeypatch, api, enqueue=True, tasks=2)
    created_by_v1 = len(api.enqueued)
    monkeypatch.setattr("discovery_ingest.worker.llm_enqueue.PROMPT_VERSION", "ext-next")
    _render(monkeypatch, api, enqueue=True)

    keys = [body["input_key"] for body in _enqueues(api)]
    assert keys[0] == keys[1] != keys[2]
    assert (created_by_v1, len(api.enqueued)) == (1, 2)


def test_an_enqueue_error_is_counted_and_logged_and_never_fails_the_render(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """after_snapshot · a 500 on the llm enqueue counts llm_enqueue_failed; the render still completes."""
    api = FakeApi([])
    api.enqueue_status = 500

    report = _render(monkeypatch, api, enqueue=True)
    quiet = _render(monkeypatch, FakeApi([]), enqueue=True)

    assert (report.completed, report.failed, report.llm_enqueue_failed) == (1, 0, 1)
    assert "llm enqueue failed" in capsys.readouterr().err
    assert quiet.llm_enqueue_failed == 0


@pytest.fixture
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setenv("CLOUDFLARE_BROWSER_API_TOKEN", "browser-token")
    monkeypatch.setenv("LLM_MODEL", MODEL)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


@pytest.mark.usefixtures("_env")
def test_the_switch_needs_a_model_and_a_render_drain_refuses_to_start_without_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · LLM_ENQUEUE=true without LLM_MODEL exits 2 naming LLM_MODEL and claims nothing."""
    api = FakeApi([[task_json(uuid.uuid4(), URL)]])
    api.client(monkeypatch)
    monkeypatch.setenv("LLM_ENQUEUE", "true")
    monkeypatch.setenv("LLM_MODEL", "")

    assert main(RENDER) == 2

    assert "LLM_MODEL" in capsys.readouterr().err
    assert api.named("complete") == [] and api.named("release") == [] and api.batches


@pytest.mark.usefixtures("_env")
def test_the_switch_defaults_to_off_and_matters_only_to_render_drains(monkeypatch: pytest.MonkeyPatch) -> None:
    """worker drain · no model is needed for a render drain with the switch off, or for a drain without render_page."""
    api = FakeApi([])
    api.client(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", "")

    assert main(RENDER) == 0
    monkeypatch.setenv("LLM_ENQUEUE", "true")
    assert main(["worker", "drain", "--kinds", "fetch_url"]) == 0

    assert _enqueues(api) == []


def _extract(monkeypatch: pytest.MonkeyPatch, reply: dict[str, object]) -> LlmApi:
    api = LlmApi([llm_task()])
    api.client(monkeypatch)
    api.cloudflare = lambda request: success(reply, {"prompt_tokens": 1000, "completion_tokens": 200})
    assert main(EXTRACT) == 0
    return api


@pytest.mark.usefixtures("_env")
def test_llm_extract_enqueues_one_capture_screenshot_when_mentions_were_posted(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · through the shared helper: one capture_screenshot (shot@1, priority 300) for the page."""
    api = _extract(monkeypatch, SERVICE)

    (shot,) = _enqueues(api)
    assert (shot["kind"], shot["input_key"], shot["priority"], shot["target_url"]) == (
        "capture_screenshot",
        "shot@1",
        300,
        llm_task()["target_url"],
    )


@pytest.mark.usefixtures("_env")
def test_llm_extract_enqueues_no_screenshot_when_no_mention_was_posted(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · a page with no documents completes without queueing a screenshot."""
    api = _extract(monkeypatch, answer(page_kind="other"))

    assert api.posts == [] and _enqueues(api) == []
