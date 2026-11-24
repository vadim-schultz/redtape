"""llm_extract skips the model when a page's cleaned text is unchanged, and records the hash of the text it read."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.extract.clean import clean_page
from discovery_ingest.extract.llm.meter import NeuronMeter
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.llm_extract import LlmExtractHandler

from extract_fakes import PAGE_URL
from llm_worker_fakes import PAGE_HTML, RUN_NEURONS, SERVICE, LlmApi, ScriptedLlm, llm_task, resources
from render_fakes import robots_fetcher

INPUT_KEY = "llm:0a1b2c3d"
OTHER_HASH = "0" * 64


def _page_hash(html: str) -> str:
    """The expected cleaned-text hash: SHA-256 of the cleaned page text, not of the raw bytes."""
    return hashlib.sha256(clean_page(html, PAGE_URL).text.encode()).hexdigest()


def _keyed_task(input_key: str | None = INPUT_KEY) -> dict[str, Any]:
    return {**llm_task(), "input_key": input_key}


def _run(api: LlmApi, llm: ScriptedLlm, monkeypatch: pytest.MonkeyPatch) -> tuple[str, NeuronMeter]:
    client: DiscoveryIngestClient = api.client(monkeypatch)
    meter = NeuronMeter(BudgetGuard(client.budget), RUN_NEURONS)
    handler = LlmExtractHandler(resources(llm), meter)
    task = ClaimedTask.model_validate(api.batches[0][0])
    return handler(task, client=client, fetcher=robots_fetcher()), meter


def _failure(api: LlmApi) -> dict[str, Any]:
    ((_task, body),) = api.named("fail")
    return body


def _note(api: LlmApi) -> str | None:
    ((_task, body),) = api.named("complete")
    return None if body is None else body["note"]


def test_an_unchanged_cleaned_text_completes_unchanged_without_a_model_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · the page's cleaned text was already extracted under these versions: zero neurons, note unchanged."""
    api = LlmApi([_keyed_task()])
    api.known_texts = {_page_hash(PAGE_HTML)}
    llm = ScriptedLlm(SERVICE)

    outcome, meter = _run(api, llm, monkeypatch)

    assert outcome == "completed"
    assert _note(api) == "unchanged"
    assert llm.calls == 0 and meter.used_neurons == 0 and api.named("reserve") == [] and api.posts == []
    (query,) = api.text_queries
    assert query["target_url"] == PAGE_URL and query["input_key"] == INPUT_KEY
    assert query["text_hash"] == _page_hash(PAGE_HTML)
    assert query["catalogue_service_id"] == str(api.batches[0][0]["catalogue_service_id"])


def test_a_changed_cleaned_text_calls_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · a cleaned text no completed extraction has read is extracted by the model as before."""
    api = LlmApi([_keyed_task()])
    api.known_texts = {OTHER_HASH}
    llm = ScriptedLlm(SERVICE)

    outcome, _meter = _run(api, llm, monkeypatch)

    assert outcome == "completed" and llm.calls == 1
    assert _note(api) == "docs=2 edges=1 dropped=0"


def test_a_task_without_a_version_key_always_calls_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · without an input key the versions are unknown, so the text is not matched and the model runs."""
    api = LlmApi([_keyed_task(input_key=None)])
    api.known_texts = {_page_hash(PAGE_HTML)}
    llm = ScriptedLlm(SERVICE)

    _run(api, llm, monkeypatch)

    assert llm.calls == 1 and api.text_queries == []


def test_a_completed_extraction_records_the_hash_of_the_text_it_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · the completion of a model run carries the cleaned-text hash the model read."""
    api = LlmApi([_keyed_task()])
    llm = ScriptedLlm(SERVICE)

    _run(api, llm, monkeypatch)

    ((_task, body),) = api.named("complete")
    assert body["text_hash"] == _page_hash(PAGE_HTML)


def test_markup_that_leaves_the_cleaned_text_alone_keeps_the_page_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · a changed nonce in the raw markup does not change the cleaned text, so the page stays unchanged."""
    raw = PAGE_HTML.replace("</main>", "</main><!-- render nonce 4711 -->")
    api = LlmApi([_keyed_task()], html=raw)
    api.known_texts = {_page_hash(PAGE_HTML)}
    llm = ScriptedLlm(SERVICE)

    outcome, _meter = _run(api, llm, monkeypatch)

    assert outcome == "completed" and llm.calls == 0
    assert _note(api) == "unchanged"


def test_an_api_without_the_check_route_still_gets_the_model_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · an API that does not serve the check (404, the route is new) runs the model as before, never fails the task."""
    api = LlmApi([_keyed_task()])
    api.text_status = 404
    llm = ScriptedLlm(SERVICE)

    outcome, _meter = _run(api, llm, monkeypatch)

    assert outcome == "completed" and llm.calls == 1
    assert _note(api) == "docs=2 edges=1 dropped=0"
    assert api.named("fail") == []


def test_a_server_error_on_the_check_fails_the_task_retryably_without_a_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · a 5xx on the check is not read as unchanged or as a go-ahead: the task fails retryably, no model call."""
    api = LlmApi([_keyed_task()])
    api.text_status = 500
    llm = ScriptedLlm(SERVICE)

    outcome, meter = _run(api, llm, monkeypatch)

    assert outcome == "failed" and llm.calls == 0 and meter.used_neurons == 0
    assert _failure(api)["retryable"] is True
