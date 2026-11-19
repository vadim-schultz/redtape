"""Each pipeline stage state has a happy and a negative test; the rules run in order and the first match wins."""

from __future__ import annotations

from app.features.discovery.flow.state import StageFacts, StageState, classify_stage
from app.features.discovery.flow.thresholds import DEFAULT_THRESHOLDS
from app.features.discovery.flow.topology import STAGE_BY_ID

RENDER = STAGE_BY_ID["render"]
"""A daily stage: overdue after 36 h, backlogged once its queue takes more than 48 h to clear."""


def _facts(
    *,
    has_producer: bool = True,
    ready: int = 0,
    completed_24h: int = 0,
    failed_24h: int = 0,
    last_stop_reason: str | None = None,
    last_run_age_hours: float | None = None,
    upstream_overdue: bool = False,
    has_headroom: bool = False,
    allotment_full: bool = False,
) -> StageFacts:
    return StageFacts(
        has_producer=has_producer,
        ready=ready,
        completed_24h=completed_24h,
        failed_24h=failed_24h,
        last_stop_reason=last_stop_reason,
        last_run_age_hours=last_run_age_hours,
        upstream_overdue=upstream_overdue,
        has_headroom=has_headroom,
        allotment_full=allotment_full,
    )


def _classify(facts: StageFacts) -> StageState:
    return classify_stage(RENDER, facts, DEFAULT_THRESHOLDS)


def test_a_stage_with_no_producer_is_dead() -> None:
    assert _classify(_facts(has_producer=False)) == StageState.DEAD


def test_a_stage_with_a_producer_is_not_dead() -> None:
    assert _classify(_facts(has_producer=True)) == StageState.IDLE


def test_the_first_matching_rule_wins() -> None:
    facts = _facts(has_producer=False, ready=5, last_stop_reason="browser_budget")

    assert _classify(facts) == StageState.DEAD


def test_a_stage_stopped_on_a_budget_with_ready_work_is_budget_stopped() -> None:
    assert _classify(_facts(ready=5, last_stop_reason="browser_budget")) == StageState.BUDGET_STOPPED


def test_a_budget_stop_without_ready_work_is_not_budget_stopped() -> None:
    assert _classify(_facts(ready=0, last_stop_reason="browser_budget")) == StageState.IDLE


def test_ready_work_with_headroom_and_a_clock_stop_is_throttled() -> None:
    facts = _facts(ready=5, has_headroom=True, last_stop_reason="time_budget")

    assert _classify(facts) == StageState.THROTTLED


def test_ready_work_with_the_allotment_full_is_not_throttled() -> None:
    facts = _facts(ready=5, has_headroom=False, allotment_full=True, last_stop_reason="time_budget")

    assert _classify(facts) == StageState.BUDGET_STOPPED


def test_nothing_ready_and_the_upstream_overdue_is_blocked() -> None:
    assert _classify(_facts(ready=0, upstream_overdue=True)) == StageState.BLOCKED


def test_nothing_ready_and_the_upstream_on_time_is_not_blocked() -> None:
    assert _classify(_facts(ready=0, upstream_overdue=False)) == StageState.IDLE


def test_nothing_ready_and_the_last_run_queue_empty_is_starved() -> None:
    facts = _facts(ready=0, last_stop_reason="queue_empty", last_run_age_hours=2.0)

    assert _classify(facts) == StageState.STARVED


def test_ready_work_that_is_moving_is_not_starved() -> None:
    facts = _facts(ready=3, completed_24h=10, last_stop_reason="queue_empty")

    assert _classify(facts) == StageState.FLOWING


def test_a_run_older_than_1_5_times_the_cadence_is_overdue() -> None:
    facts = _facts(last_run_age_hours=37.0, last_stop_reason="batch_limit")

    assert _classify(facts) == StageState.OVERDUE


def test_a_run_exactly_1_5_times_the_cadence_is_not_overdue() -> None:
    facts = _facts(last_run_age_hours=36.0, last_stop_reason="batch_limit")

    assert _classify(facts) == StageState.IDLE


def test_a_backlog_taking_more_than_twice_the_cadence_to_clear_is_backlogged() -> None:
    assert _classify(_facts(ready=500, completed_24h=10)) == StageState.BACKLOGGED


def test_a_backlog_clearing_within_twice_the_cadence_is_not_backlogged() -> None:
    assert _classify(_facts(ready=100, completed_24h=100)) == StageState.FLOWING


def test_a_stage_that_completed_work_in_a_day_is_flowing() -> None:
    facts = _facts(completed_24h=5, last_stop_reason="batch_limit", last_run_age_hours=1.0)

    assert _classify(facts) == StageState.FLOWING


def test_a_stage_that_completed_nothing_in_a_day_is_not_flowing() -> None:
    facts = _facts(completed_24h=0, last_stop_reason="batch_limit", last_run_age_hours=1.0)

    assert _classify(facts) == StageState.IDLE


def test_a_stage_with_nothing_to_do_is_idle() -> None:
    assert _classify(_facts()) == StageState.IDLE


def test_ready_work_that_is_not_moving_is_backlogged_not_idle() -> None:
    assert _classify(_facts(ready=5)) == StageState.BACKLOGGED
