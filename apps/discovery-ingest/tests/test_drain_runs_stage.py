"""Every drain records one run with its stage, its counts, its stop reason and its spend (chapter 2 of the pipeline suite)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.config import IngestSettings
from discovery_ingest.operations import embed_drain, snapshot_drain, translate_drain
from discovery_ingest.schemas import DrainReport, RunFinishRequest
from discovery_ingest.worker import run as run_module
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.llm_setup import EXIT_NOT_READY, LlmSetupError
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.run import run_recorded_drain
from pydantic import SecretStr

from drain_deps_for import deps_for
from run_stub import run_response

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client
Starts = list[dict[str, Any]]
Finishes = list[dict[str, Any]]


def _report(**overrides: Any) -> DrainReport:
    values: dict[str, Any] = {
        "claimed": 4,
        "completed": 3,
        "failed": 1,
        "skipped": 0,
        "stop_reason": "queue_empty",
        "browser_seconds_used": 0.0,
        "neurons_used": 12.5,
        "characters_used": 300,
    }
    values.update(overrides)
    return DrainReport(**values)


def _summary(request: httpx.Request) -> httpx.Response | None:
    """An empty queue for the two summary routes the snapshot drain reads to share the monthly characters."""
    if request.url.path.endswith(("/snapshots/summary", "/translations/summary")):
        return httpx.Response(200, json={"locales": []})
    return None


def _client(monkeypatch: pytest.MonkeyPatch, starts: Starts, finishes: Finishes) -> DiscoveryIngestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/machine/runs") and request.method == "POST":
            starts.append(json.loads(request.content))
        stub = _summary(request) or run_response(request, finishes)
        assert stub is not None, f"unexpected request {request.method} {request.url}"
        return stub

    transport = httpx.MockTransport(handler)

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
    return DiscoveryIngestClient(API_BASE, SecretStr("test-machine-key"))


@pytest.fixture(autouse=True)
def _no_real_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    """The three drains build engines from the environment; the tests replace every engine with a stand-in."""
    monkeypatch.setattr(embed_drain, "_check_credentials", lambda settings: None)
    monkeypatch.setattr(embed_drain, "_check_ledger", lambda client: None)
    monkeypatch.setattr(embed_drain, "CloudflareEmbeddingClient", lambda *args, **kwargs: object())
    monkeypatch.setattr(translate_drain, "build_translation_engine", lambda settings, http, interval: object())
    monkeypatch.setattr(translate_drain, "_drain_deps", lambda client, engine, settings: object())
    monkeypatch.setattr(snapshot_drain, "_azure_engine", lambda http: object())


Drain = Callable[[DiscoveryIngestClient], DrainReport]
DRAINS: list[tuple[str, Drain, str, Any, str]] = []
"""Each drain entry point, the stage it must record, and the module attribute that runs its batches."""


def _run_embed(client: DiscoveryIngestClient) -> DrainReport:
    return embed_drain.run_embed(embed_drain.EmbedOptions(), IngestSettings.model_construct(), client)


def _run_translate(client: DiscoveryIngestClient) -> DrainReport:
    return translate_drain.run_translate(translate_drain.TranslateOptions(), _settings(), client)


def _run_snapshot(client: DiscoveryIngestClient) -> DrainReport:
    return snapshot_drain.run_snapshot(snapshot_drain.SnapshotOptions(), client)


def _settings() -> Any:
    """The translation settings only reach the stand-ins, so any object will do."""
    return object()


DRAINS.extend(
    [
        ("embed", _run_embed, "embed", embed_drain, "run_embed_drain"),
        ("translate", _run_translate, "translate", translate_drain, "run_translate_drain"),
        ("snapshot", _run_snapshot, "snapshot_translate", snapshot_drain, "run_snapshot_drain"),
    ]
)
DRAIN_CASES = [(label, run, stage) for label, run, stage, _module, _name in DRAINS]


@pytest.mark.parametrize(("label", "run", "stage"), DRAIN_CASES, ids=[case[0] for case in DRAIN_CASES])
def test_each_drain_records_one_run_with_its_stage(
    monkeypatch: pytest.MonkeyPatch, label: str, run: Drain, stage: str
) -> None:
    """embed, translate and snapshot drains · one run is opened with the drain's stage and finished with its counts."""
    starts: Starts = []
    finishes: Finishes = []
    client = _client(monkeypatch, starts, finishes)
    module, name = _inner(label)
    monkeypatch.setattr(module, name, lambda *args, **kwargs: _report())

    run(client)

    assert [start["stage"] for start in starts] == [stage]
    assert len(finishes) == 1
    assert (finishes[0]["status"], finishes[0]["claimed_count"], finishes[0]["stop_reason"]) == (
        "succeeded",
        4,
        "queue_empty",
    )
    assert finishes[0]["spend"]["neurons"] == 12.5


def _inner(label: str) -> tuple[Any, str]:
    entry = next(item for item in DRAINS if item[0] == label)
    return entry[3], entry[4]


@pytest.mark.parametrize(("label", "run", "stage"), DRAIN_CASES, ids=[case[0] for case in DRAIN_CASES])
def test_a_drain_that_raises_closes_its_run_as_failed_with_its_stage(
    monkeypatch: pytest.MonkeyPatch, label: str, run: Drain, stage: str
) -> None:
    """embed, translate and snapshot drains · an error inside the drain closes the run as failed, with its stage, and is raised again."""
    starts: Starts = []
    finishes: Finishes = []
    client = _client(monkeypatch, starts, finishes)
    module, name = _inner(label)

    def crash(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("the drain crashed")

    monkeypatch.setattr(module, name, crash)

    with pytest.raises(RuntimeError, match="the drain crashed"):
        run(client)

    assert [start["stage"] for start in starts] == [stage]
    assert len(finishes) == 1
    assert (finishes[0]["status"], finishes[0]["stop_reason"]) == ("failed", "error")
    assert "RuntimeError" in finishes[0]["error_detail"]


def test_a_refusal_before_the_drain_opens_no_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """embed drain · missing credentials are refused before any run is opened, so the refusal leaves no run record."""
    starts: Starts = []
    finishes: Finishes = []
    client = _client(monkeypatch, starts, finishes)

    def refuse(settings: Any) -> None:
        raise LlmSetupError("embed drain needs these environment variables", EXIT_NOT_READY)

    monkeypatch.setattr(embed_drain, "_check_credentials", refuse)

    with pytest.raises(LlmSetupError):
        _run_embed(client)

    assert (starts, finishes) == ([], [])


def test_the_worker_drain_still_records_its_run_as_a_worker_drain(monkeypatch: pytest.MonkeyPatch) -> None:
    """worker drain · the run it opens names worker_drain as its stage, as before the stage existed."""
    starts: Starts = []
    finishes: Finishes = []
    client = _client(monkeypatch, starts, finishes)
    monkeypatch.setattr(run_module, "run_worker_drain", lambda deps, policy: _report(browser_seconds_used=6.5))

    run_recorded_drain(deps_for(client, PoliteUrlFetcher()), DrainPolicy())

    assert [start["stage"] for start in starts] == ["worker_drain"]
    assert finishes[0]["spend"] == {"browser_seconds": 6.5, "neurons": 12.5, "azure_translator_chars": 300.0}


def test_a_run_that_fails_keeps_the_spend_its_report_already_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    """spend · a drain that ends on an infrastructure error still reports what it spent before the error."""
    finishes: Finishes = []
    client = _client(monkeypatch, [], finishes)
    failed = _report(error="storage down", stop_reason="error", succeeded=False, browser_seconds_used=2.0)
    monkeypatch.setattr(run_module, "run_worker_drain", lambda deps, policy: failed)

    run_recorded_drain(deps_for(client, PoliteUrlFetcher()), DrainPolicy())

    assert (finishes[0]["status"], finishes[0]["spend"]["browser_seconds"]) == ("failed", 2.0)


def test_the_finish_request_carries_only_the_resources_the_drains_spend() -> None:
    """spend · the spend dict has the three drain resources and nothing else, so the API's validation accepts it."""
    body = RunFinishRequest(
        status="succeeded",
        claimed_count=0,
        completed_count=0,
        failed_count=0,
        skipped_count=0,
        spend={"browser_seconds": 1.0, "neurons": 2.0, "azure_translator_chars": 3.0},
    )

    assert set(body.model_dump(mode="json")["spend"]) == {"browser_seconds", "neurons", "azure_translator_chars"}


def test_run_start_sends_the_kind_and_the_stage_it_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    """runs API · start names the kind and the stage, and defaults both to worker_drain."""
    starts: Starts = []
    client = _client(monkeypatch, starts, [])

    client.runs.start("worker_drain", "embed")
    client.runs.start()

    assert starts == [{"kind": "worker_drain", "stage": "embed"}, {"kind": "worker_drain", "stage": "worker_drain"}]
