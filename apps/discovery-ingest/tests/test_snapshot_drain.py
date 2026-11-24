"""Snapshot drain: claim pages, fetch them, run the pipeline, translate the blocks under the document share, settle each task.

The unchanged page costs nothing, a skipped page is marked, a pruned page is released without an attempt, and a
denial or a quota stop releases the tasks nobody settled (azure-translation chapter 11).
"""

from __future__ import annotations

from datetime import date

import pytest
from discovery_ingest.operations.snapshot_drain import (
    Pacing,
    SnapshotDeps,
    SnapshotOptions,
    adaptive_share,
    daily_allowance,
    document_budget_share,
    load_pacing_settings,
    run_snapshot_drain,
    window_end,
)
from discovery_ingest.schemas import DrainReport
from discovery_ingest.snapshot_translation import prepare_page
from discovery_ingest.translation.errors import QuotaExceeded, RateLimited, TransientError
from discovery_ingest.worker.llm_setup import LlmSetupError

from ledger_fakes import CHARACTERS, FakeLedger
from snapshot_fakes import (
    ENGINE,
    EXPECTED_KINDS,
    VANISH,
    ScriptedAzure,
    SnapshotApi,
    artifact_id,
    page_html,
    page_url,
    sha,
    short_page,
    snapshot_task,
    task_id,
)
from translate_fakes import API_KEY

FLOOR_REMAINING = 760_000.0
"""What the monthly ledger holds when the document share (60% of the 1,900,000 cap) is used up."""
JUST_ABOVE_FLOOR = FLOOR_REMAINING + 100.0
"""A ledger 100 characters above the floor: any page of a few hundred characters is then denied."""


def _drain(
    api: SnapshotApi,
    engine: ScriptedAzure,
    *,
    max_tasks: int = 5,
    max_batches: int = 10,
    share: float = 0.6,
) -> DrainReport:
    deps = SnapshotDeps(api.client(), engine, share=share)
    return run_snapshot_drain(deps, SnapshotOptions(max_tasks=max_tasks, max_batches=max_batches).policy())


def _stored_hash(number: int) -> str:
    """The cleaned-text hash the page of task ``number`` has, as it would be stored once translated."""
    return prepare_page(page_html(), page_url(number)).source_hash


def _characters_left(ledger: FakeLedger) -> float:
    assert ledger.characters is not None
    return ledger.characters.remaining


def test_drain_an_unchanged_page_completes_with_zero_characters_reserved_and_no_engine_call() -> None:
    """Drain · an unchanged page completes with zero characters reserved and no engine call."""
    api = SnapshotApi([snapshot_task(0, stored=_stored_hash(0))], {0: page_html()})
    engine = ScriptedAzure()

    report = _drain(api, engine)

    [item] = api.posted()
    assert (item["task_id"], item["outcome"], item["source_hash"]) == (task_id(0), "unchanged", _stored_hash(0))
    assert engine.batches == [] and api.ledger.writes_to(CHARACTERS) == []
    assert (report.characters_used, report.unchanged, report.completed) == (0, 1, 1)


def test_drain_a_changed_page_translates_each_block_into_the_target_locale_and_completes_with_blocks() -> None:
    """Drain · a changed page translates each block into the target locale and completes with blocks."""
    api = SnapshotApi([snapshot_task(0, "en")], {0: page_html()})
    engine = ScriptedAzure()

    report = _drain(api, engine)

    [batch] = engine.batches
    assert (batch.source_locale, batch.target_locale) == ("de", "en")
    [item] = api.posted()
    assert (item["outcome"], item["engine"], item["model"], item["truncated"]) == ("translated", ENGINE, None, False)
    assert (item["artifact_sha256"], item["source_hash"]) == (sha(0), _stored_hash(0))
    assert [block["kind"] for block in item["blocks"]] == EXPECTED_KINDS
    assert item["blocks"][0] == {"kind": "h1", "text": "[en] Reisepass beantragen"}
    assert item["blocks"][7] == {"kind": "row", "cells": ["[en] Art", "[en] Preis"]}
    assert item["blocks"][9] == {"kind": "p", "text": "[en] Mehr unter Infos (https://www.example.de/info)."}
    assert (report.completed, report.llm_calls, report.untranslated_blocks) == (1, 1, 0)


def test_drain_the_characters_settled_equal_the_billed_figure() -> None:
    """Drain · the characters settled equal the billed figure, not the estimate."""
    ledger = FakeLedger(9000.0, characters=1_900_000.0)
    api = SnapshotApi([snapshot_task(0)], {0: page_html()}, ledger=ledger)
    engine = ScriptedAzure(billed=0.9)

    report = _drain(api, engine)

    assert engine.billed_total < engine.estimated_total
    assert report.characters_used == round(engine.billed_total)
    assert _characters_left(ledger) == pytest.approx(1_900_000.0 - engine.billed_total)


@pytest.mark.parametrize(("html", "reason"), [(short_page(), "too_short"), (page_html(lang="en"), "not_german")])
def test_drain_a_skipped_page_completes_with_its_skip_reason(html: str, reason: str) -> None:
    """Drain · a skipped page completes with its skip reason and no characters."""
    api = SnapshotApi([snapshot_task(0)], {0: html})
    engine = ScriptedAzure()

    report = _drain(api, engine)

    [item] = api.posted()
    assert (item["outcome"], item["skipped_reason"]) == ("skipped", reason)
    assert engine.batches == [] and (report.skipped, report.characters_used) == (1, 0)


def test_drain_a_stale_answer_is_tallied_and_neither_failed_nor_released() -> None:
    """Drain · a stale answer is tallied as stale; the server requeues the task, so the drain neither fails nor releases it."""
    api = SnapshotApi([snapshot_task(0)], {0: page_html()})
    api.outcomes[task_id(0)] = ("stale", None)

    report = _drain(api, ScriptedAzure())

    assert (report.completed, report.stale, report.failed, report.released) == (1, 1, 0, 0)
    assert api.bodies["fail"] == [] and api.bodies["release"] == []


def test_drain_claims_at_most_five_tasks_and_counts_every_skipped_one() -> None:
    """Drain · a batch claims five pages at most, and the drain goes on until the queue is empty."""
    api = SnapshotApi([snapshot_task(n) for n in range(7)], {n: short_page() for n in range(7)})

    report = _drain(api, ScriptedAzure())

    assert [body["limit"] for body in api.bodies["claim"]] == [5, 5, 5]
    assert (report.claimed, report.skipped, report.stop_reason) == (7, 7, "queue_empty")


def test_drain_a_reservation_that_would_breach_the_document_floor_is_denied_tasks_are_released_and_attempts_unchanged() -> (
    None
):
    """Drain · a reservation that would breach the document floor is denied; tasks are released and attempt_count is unchanged."""
    ledger = FakeLedger(9000.0, characters=JUST_ABOVE_FLOOR)
    api = SnapshotApi([snapshot_task(0)], {0: page_html()}, ledger=ledger)
    engine = ScriptedAzure()

    report = _drain(api, engine)

    assert engine.batches == [] and api.bodies["fail"] == []
    assert api.bodies["release"][0]["task_ids"] == [task_id(0)]
    assert api.bodies["release"][0]["reason"].startswith("llm_budget")
    assert (report.stop_reason, report.succeeded, report.released, report.completed) == ("llm_budget", True, 1, 0)
    assert _characters_left(ledger) == JUST_ABOVE_FLOOR


def test_drain_a_denial_releases_the_open_tasks_and_keeps_the_settled_ones() -> None:
    """Drain · a denial releases the tasks nobody has settled and keeps the ones already posted."""
    ledger = FakeLedger(9000.0, characters=JUST_ABOVE_FLOOR)
    tasks = [snapshot_task(0, stored=_stored_hash(0)), snapshot_task(1), snapshot_task(2)]
    api = SnapshotApi(tasks, {0: page_html(), 1: page_html(), 2: page_html()}, ledger=ledger)

    report = _drain(api, ScriptedAzure(), max_batches=1)

    assert [item["task_id"] for item in api.posted()] == [task_id(0)]
    assert api.bodies["release"][0]["task_ids"] == [task_id(1), task_id(2)]
    assert (report.completed, report.released) == (1, 2)


def test_drain_a_404_for_a_pruned_snapshot_releases_the_task_with_snapshot_gone_and_no_attempt_used() -> None:
    """Drain · a 404 for a pruned snapshot releases the task with snapshot_gone and no attempt used."""
    api = SnapshotApi([snapshot_task(0)], {})
    engine = ScriptedAzure()

    report = _drain(api, engine, max_batches=1)

    assert api.fetched == [artifact_id(0)]
    assert api.bodies["release"] == [{"task_ids": [task_id(0)], "reason": "snapshot_gone"}]
    assert api.bodies["fail"] == [] and engine.batches == []
    assert (report.pruned, report.released, report.failed) == (1, 1, 0)


def test_drain_one_block_failing_validation_is_posted_as_untranslated_and_the_page_still_completes() -> None:
    """Drain · one block failing validation is posted with its German text and the page still completes."""
    german = f"{VANISH} Hinweis zum Antrag bei der Behörde."
    api = SnapshotApi([snapshot_task(0)], {0: page_html(extra=f"<p>{german}</p>")})

    report = _drain(api, ScriptedAzure())

    [item] = api.posted()
    assert item["outcome"] == "translated" and item["blocks"][0]["text"] == "[en] Reisepass beantragen"
    assert item["blocks"][-1] == {"kind": "p", "text": german, "untranslated": True}
    assert (report.completed, report.untranslated_blocks, report.failed) == (1, 1, 0)


def test_drain_only_the_block_that_kept_its_german_text_is_marked_untranslated() -> None:
    """Drain · the good blocks of a page are not marked untranslated; only the block that kept its German text is."""
    german = f"{VANISH} Hinweis zum Antrag bei der Behörde."
    api = SnapshotApi([snapshot_task(0)], {0: page_html(extra=f"<p>{german}</p>")})

    _drain(api, ScriptedAzure())

    [item] = api.posted()
    flags = [block.get("untranslated", False) for block in item["blocks"]]
    assert flags == [False] * len(EXPECTED_KINDS) + [True]


def test_drain_a_structural_mismatch_fails_the_task_with_its_reason_in_last_error() -> None:
    """Drain · a structural mismatch fails the task permanently with its reason in last_error."""
    api = SnapshotApi([snapshot_task(0)], {0: page_html()})

    report = _drain(api, ScriptedAzure(short=True))

    [failure] = api.bodies["fail"]
    assert (failure["task_id"], failure["retryable"]) == (task_id(0), False)
    assert failure["error"] == "the translation has 9 blocks, the source has 10"
    assert (report.failed, report.invalid, report.completed) == (1, 1, 0)


def test_drain_an_unreadable_ledger_sends_no_fetch_and_no_engine_call() -> None:
    """Drain · an unreadable ledger sends no claim, no fetch and no engine call."""
    api = SnapshotApi([snapshot_task(0)], {0: page_html()}, ledger=FakeLedger(9000.0, characters=1.0, down=True))
    engine = ScriptedAzure()

    with pytest.raises(LlmSetupError):
        _drain(api, engine)

    assert api.bodies["claim"] == [] and api.fetched == [] and engine.batches == []


def test_drain_a_403001_calls_exhaust_once_and_stops_the_drain() -> None:
    """Drain · a 403001 calls exhaust once and stops the drain; the batch's open tasks are released."""
    api = SnapshotApi([snapshot_task(n) for n in range(3)], {n: page_html() for n in range(3)})
    engine = ScriptedAzure(None, QuotaExceeded("403001: the free quota is used up"))

    report = _drain(api, engine)

    assert api.ledger.writes_to(CHARACTERS).count("exhaust") == 1
    assert (report.stop_reason, report.succeeded, report.completed) == ("llm_quota", True, 1)
    assert api.bodies["release"][0]["task_ids"] == [task_id(1), task_id(2)]
    assert api.bodies["fail"] == []


def test_drain_a_transient_engine_error_fails_only_that_page_and_it_may_be_retried() -> None:
    """Drain · a transient engine error fails only its own page, retryably; the other pages still complete."""
    api = SnapshotApi([snapshot_task(0), snapshot_task(1)], {0: page_html(), 1: page_html()})

    report = _drain(api, ScriptedAzure(TransientError("429001: throttled"), None))

    [failure] = api.bodies["fail"]
    assert (failure["task_id"], failure["retryable"]) == (task_id(0), True)
    assert (report.failed, report.completed, report.stop_reason) == (1, 1, "queue_empty")


def test_drain_the_api_key_never_appears_in_logs_or_the_report(capsys: pytest.CaptureFixture[str]) -> None:
    """Drain · the API key never appears in logs or the report."""
    api = SnapshotApi([snapshot_task(0), snapshot_task(1)], {0: page_html(), 1: page_html()})

    report = _drain(api, ScriptedAzure(TransientError("the call failed"), None))

    captured = capsys.readouterr()
    assert API_KEY not in captured.out + captured.err
    assert API_KEY not in report.model_dump_json()


def test_drain_when_the_document_share_is_used_up_no_task_is_claimed() -> None:
    """Drain · when the document share is used up no batch is claimed, so no page is fetched."""
    api = SnapshotApi([snapshot_task(0)], {0: page_html()}, ledger=FakeLedger(9000.0, characters=FLOOR_REMAINING))

    report = _drain(api, ScriptedAzure())

    assert (report.stop_reason, report.claimed) == ("llm_budget", 0)
    assert api.bodies["claim"] == [] and api.fetched == []


def test_the_document_share_defaults_to_0_6_and_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drain · AZURE_DOCUMENT_BUDGET_SHARE defaults to 0.6 and is read from the worker's environment."""
    monkeypatch.delenv("AZURE_DOCUMENT_BUDGET_SHARE", raising=False)
    assert document_budget_share() == 0.6

    monkeypatch.setenv("AZURE_DOCUMENT_BUDGET_SHARE", "0.5")
    assert document_budget_share() == 0.5


def test_drain_a_rate_limited_page_releases_the_batch_without_an_attempt_and_stops_the_drain() -> None:
    """Drain · a 429 releases every open task without an attempt, stops with rate_limited, and no second claim follows."""
    api = SnapshotApi([snapshot_task(n) for n in range(3)], {n: page_html() for n in range(3)})

    report = _drain(api, ScriptedAzure(RateLimited("429000: slow down", retry_after=5.0)))

    claims = [path for path in api.paths if path.endswith("/claim")]
    assert (report.stop_reason, report.succeeded, report.released, report.failed) == ("rate_limited", True, 3, 0)
    assert api.bodies["fail"] == [] and api.bodies["release"][0]["task_ids"] == [task_id(n) for n in range(3)]
    assert len(claims) == 1


def test_the_window_anchor_defaults_to_2026_11_13_and_changes_with_its_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pacing · the window anchor is 2026-11-13 (UTC) by default, and AZURE_WINDOW_ANCHOR moves it and the window with it."""
    monkeypatch.delenv("AZURE_WINDOW_ANCHOR", raising=False)
    assert load_pacing_settings().window_anchor == date(2026, 11, 13)
    assert window_end(date(2026, 11, 13), date(2026, 11, 15)) == date(2026, 12, 13)

    monkeypatch.setenv("AZURE_WINDOW_ANCHOR", "2026-11-01")
    assert load_pacing_settings().window_anchor == date(2026, 11, 1)
    assert window_end(date(2026, 11, 1), date(2026, 11, 15)) == date(2026, 12, 1)


def test_the_daily_pace_carries_an_unspent_amount_to_the_next_day() -> None:
    """Pacing · what day one leaves unspent stays in the remaining amount, so day two's allowance is larger than day one's."""
    anchor = date(2026, 11, 13)
    day_one = daily_allowance(1_900_000.0, anchor=anchor, today=date(2026, 11, 13))
    day_two = daily_allowance(1_900_000.0 - 20_000.0, anchor=anchor, today=date(2026, 11, 14))

    assert day_one == pytest.approx(1_900_000.0 / 30)
    assert day_two == pytest.approx(1_880_000.0 / 29) and day_two > day_one


def test_the_daily_pace_setting_replaces_the_computed_allowance() -> None:
    """Pacing · AZURE_DAILY_CHAR_PACE, when set, is the day's allowance; unset, the allowance is computed."""
    anchor = date(2026, 11, 13)

    assert daily_allowance(1_900_000.0, anchor=anchor, today=date(2026, 11, 13), daily_pace=5_000.0) == 5_000.0


def test_a_run_may_not_spend_more_than_todays_pace_and_its_pages_are_released() -> None:
    """Drain · a run whose page would take it past the daily pace is denied, and the page is released without an attempt."""
    api = SnapshotApi([snapshot_task(0)], {0: page_html()})
    deps = SnapshotDeps(api.client(), ScriptedAzure(), pacing=Pacing(daily_pace=10.0))

    report = run_snapshot_drain(deps, SnapshotOptions(max_tasks=5, max_batches=10).policy())

    assert (report.stop_reason, report.released, report.llm_calls) == ("llm_budget", 1, 0)
    assert api.bodies["fail"] == []


@pytest.mark.parametrize(("documents", "cards", "share"), [(0, 4200, 0.0), (300, 700, 0.3), (5000, 500, 0.6)])
def test_the_adaptive_share_is_the_documents_part_of_the_demand_and_never_above_the_card_band_limit(
    documents: int, cards: int, share: float
) -> None:
    """Pacing · the documents' share follows their part of the pending demand, and cards keep at least 40% of the cap."""
    assert adaptive_share(documents, cards, ceiling=0.6) == pytest.approx(share)
