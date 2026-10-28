"""llm_extract: the pipeline from a stored snapshot to staged mentions and edges, with a fake model (chapter E6, A)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.edges import EdgeItem
from discovery_ingest.extract.llm.errors import LlmInvalidOutput
from discovery_ingest.extract.llm.meter import NeuronMeter
from discovery_ingest.extract.llm.prices import cost
from discovery_ingest.mentions import MentionItem
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.llm_extract import LlmExtractHandler
from discovery_ingest.worker.llm_post import post_staged

from llm_worker_fakes import (
    MODEL,
    PAGE_HTML,
    RUN_NEURONS,
    SERVICE,
    SHELL_HTML,
    LlmApi,
    ScriptedLlm,
    answer,
    llm_task,
    resources,
)
from render_fakes import CATALOGUE_ID, robots_fetcher

Outcome = tuple[str, NeuronMeter]


def _setup(monkeypatch: pytest.MonkeyPatch, api: LlmApi) -> tuple[DiscoveryMachineClient, NeuronMeter]:
    client = api.client(monkeypatch)
    return client, NeuronMeter(BudgetGuard(client), RUN_NEURONS)


def _run(
    monkeypatch: pytest.MonkeyPatch,
    api: LlmApi,
    llm: ScriptedLlm,
    after: Callable[[DiscoveryMachineClient, ClaimedTask], bool] | None = None,
) -> Outcome:
    client, meter = _setup(monkeypatch, api)
    handler = LlmExtractHandler(resources(llm), meter, *([after] if after else []))
    task = ClaimedTask.model_validate(api.batches[0][0])
    return handler(task, client=client, fetcher=robots_fetcher()), meter


def _note(api: LlmApi) -> str | None:
    ((_task, body),) = api.named("complete")
    return None if body is None else body["note"]


def _failure(api: LlmApi) -> dict[str, Any]:
    ((_task, body),) = api.named("fail")
    return body


def test_a_snapshot_is_read_called_once_posted_in_order_settled_and_completed_with_a_counts_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · mentions then the derived edge, settled at the real cost, note docs=2 edges=1 dropped=0."""
    api, llm = LlmApi([llm_task()]), ScriptedLlm(SERVICE)

    outcome, meter = _run(monkeypatch, api, llm)

    assert outcome == "completed" and llm.calls == 1
    assert api.posts == ["mentions", "edges"]
    assert api.mention_titles() == ["Reisepass", "Meldebescheinigung"]
    assert api.edge_posts[0][0]["parent_title_i18n"] == {"de": "Meldebescheinigung"}
    assert _note(api) == "docs=2 edges=1 dropped=0"
    assert meter.used_neurons == pytest.approx(cost(MODEL, 1000, 200))
    assert api.ledger_remaining == pytest.approx(9000 - cost(MODEL, 1000, 200))


@pytest.mark.parametrize("html", [SHELL_HTML, "<html><body><main><p>Kurz.</p></main></body></html>"])
def test_a_page_with_no_usable_text_completes_with_no_content_and_never_reserves_or_calls(
    monkeypatch: pytest.MonkeyPatch, html: str
) -> None:
    """llm_extract · an empty or near-empty cleaned page costs nothing: no reservation, no model call, no post."""
    api, llm = LlmApi([llm_task()], html), ScriptedLlm(SERVICE)

    outcome, meter = _run(monkeypatch, api, llm)

    assert outcome == "completed" and _note(api) == "no_content"
    assert llm.calls == 0 and api.named("reserve") == [] and meter.used_neurons == 0 and api.posts == []


@pytest.mark.parametrize(
    ("reply", "note"),
    [
        (answer(page_kind="login_or_error"), "login_wall"),
        (answer(page_kind="other"), "no_documents"),
        (answer(), "no_documents"),
        (answer({"name": "Phantom", "role": "required", "quote": "not on the page"}), "no_documents"),
    ],
)
def test_a_login_or_empty_extraction_completes_with_its_note_and_posts_nothing(
    monkeypatch: pytest.MonkeyPatch, reply: dict[str, Any], note: str
) -> None:
    """llm_extract · login_or_error, other, no items or nothing grounded complete with a note and post nothing."""
    api, llm = LlmApi([llm_task()]), ScriptedLlm(reply)

    outcome, meter = _run(monkeypatch, api, llm)

    assert outcome == "completed" and _note(api) == note
    assert api.posts == [] and llm.calls == 1 and meter.used_neurons == pytest.approx(cost(MODEL, 1000, 200))


def _mentions(count: int) -> list[MentionItem]:
    return [
        MentionItem(
            catalogue_service_id=CATALOGUE_ID,
            title_i18n={"de": f"Dokument {number}"},
            role="required",
            excerpt="x",
            source_field="llm",
            extractor="llm",
            extractor_version="ext-1",
        )
        for number in range(count)
    ]


def _edges(count: int) -> list[EdgeItem]:
    return [
        EdgeItem(
            catalogue_service_id=CATALOGUE_ID,
            parent_title_i18n={"de": "Antrag"},
            required_title_i18n={"de": f"Dokument {number}"},
            basis="explicit",
            excerpt="x",
            extractor="llm",
            extractor_version="ext-1",
        )
        for number in range(count)
    ]


def test_mentions_are_posted_before_edges_in_chunks_of_at_most_100(monkeypatch: pytest.MonkeyPatch) -> None:
    """post_staged · 250 mentions and 101 edges go as 100+100+50 then 100+1, mentions first; unknown codes add up."""
    api = LlmApi([])
    client = api.client(monkeypatch)
    api.unknown_codes = 1

    unknown = post_staged(client, _mentions(250), _edges(101))

    assert api.posts == ["mentions"] * 3 + ["edges"] * 2
    assert [len(post) for post in api.mention_posts] == [100, 100, 50]
    assert [len(post) for post in api.edge_posts] == [100, 1]
    assert unknown == 3


def test_a_refused_mention_batch_stops_before_any_edge_is_posted(monkeypatch: pytest.MonkeyPatch) -> None:
    """post_staged · edges need their endpoints, so a failed mention post raises before the edges route is called."""
    api = LlmApi([])
    client = api.client(monkeypatch)
    api.mention_status = 500

    with pytest.raises(Exception, match="500"):
        post_staged(client, _mentions(2), _edges(1))

    assert api.posts == ["mentions"]


def test_the_unknown_codes_of_the_api_reach_the_completion_note(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · codes the API dropped are counted into the note next to the grounding drops."""
    api, llm = LlmApi([llm_task()]), ScriptedLlm(SERVICE)
    api.unknown_codes = 2

    _run(monkeypatch, api, llm)

    assert _note(api) == "docs=2 edges=1 dropped=0 unknown_codes=2"


def test_the_screenshot_helper_runs_once_when_a_mention_was_posted_and_not_otherwise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · after hook once with mentions; never for no_content or an empty extraction; a False answer is counted."""
    seen: list[uuid.UUID] = []

    def after(client: DiscoveryMachineClient, task: ClaimedTask) -> bool:
        seen.append(task.id)
        return False

    posted = LlmApi([llm_task()])
    outcome, _ = _run(monkeypatch, posted, ScriptedLlm(SERVICE), after)
    assert outcome == "completed_capture_enqueue_failed" and len(seen) == 1

    seen.clear()
    for html, reply in ((SHELL_HTML, SERVICE), (PAGE_HTML, answer())):
        quiet = LlmApi([llm_task()], html)
        assert _run(monkeypatch, quiet, ScriptedLlm(reply), after)[0] == "completed"
    assert seen == []


@pytest.mark.parametrize(("status", "retryable"), [(404, False), (500, True)])
def test_a_missing_artifact_fails_permanently_and_a_5xx_on_the_content_route_fails_retryably(
    monkeypatch: pytest.MonkeyPatch, status: int, retryable: bool
) -> None:
    """llm_extract · 404 on the content route is permanent, 500 is retryable; the model is never called."""
    api, llm = LlmApi([llm_task()]), ScriptedLlm(SERVICE)
    api.content_status = status

    outcome, _ = _run(monkeypatch, api, llm)

    assert outcome == "failed" and _failure(api)["retryable"] is retryable
    assert llm.calls == 0 and api.named("reserve") == []


def test_a_task_without_an_artifact_fails_permanently(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · no artifact_id is a malformed task: failed, not retried, nothing called."""
    api, llm = LlmApi([llm_task(artifact_id=None)]), ScriptedLlm(SERVICE)

    outcome, _ = _run(monkeypatch, api, llm)

    assert outcome == "failed" and _failure(api)["retryable"] is False and llm.calls == 0


@pytest.mark.parametrize("first", ["not json {", LlmInvalidOutput("the model answer is not valid JSON")])
def test_an_invalid_output_is_retried_once_under_a_second_reservation(
    monkeypatch: pytest.MonkeyPatch, first: str | LlmInvalidOutput
) -> None:
    """llm_extract · the first answer is unusable, the repair call (second reservation, with a hint) succeeds."""
    api, llm = LlmApi([llm_task()]), ScriptedLlm(first, SERVICE)

    outcome, _ = _run(monkeypatch, api, llm)

    assert outcome == "completed" and llm.calls == 2 and len(api.named("reserve")) == 2
    assert "valid JSON" in llm.messages[1][-1]["content"] and len(llm.messages[1]) == len(llm.messages[0]) + 1


def test_two_invalid_outputs_fail_the_task_permanently_naming_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · the repair is not repeated: two bad answers fail the page, keep both reservations, post nothing."""
    api, llm = LlmApi([llm_task()]), ScriptedLlm("not json {")

    outcome, meter = _run(monkeypatch, api, llm)

    failure = _failure(api)
    assert outcome == "failed" and failure["retryable"] is False and MODEL in failure["error"]
    assert llm.calls == 2 and api.posts == [] and len(api.named("reserve")) == 2
    assert meter.used_neurons == pytest.approx(2 * cost(MODEL, 1000, 200))
