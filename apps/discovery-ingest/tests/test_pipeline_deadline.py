"""The pipeline deadline arithmetic: the run's seconds from the minutes left, and each stage's capped share (chapter 12)."""

from __future__ import annotations

from datetime import date

import pytest
from discovery_ingest.operations.pipeline import days_left, run_seconds, stage_seconds


def test_the_run_gets_the_actions_minutes_left_spread_over_the_days_left() -> None:
    assert run_seconds(actions_minutes_remaining=50.0, days=1) == 3000.0
    assert run_seconds(actions_minutes_remaining=60.0, days=3) == 1200.0


def test_the_run_is_capped_at_an_hour_and_never_negative() -> None:
    assert run_seconds(actions_minutes_remaining=10_000.0, days=1) == 3600.0
    assert run_seconds(actions_minutes_remaining=-5.0, days=3) == 0.0


def test_a_stage_gets_the_time_left_capped_at_twenty_minutes() -> None:
    assert stage_seconds(deadline_at=10_000.0, now=0.0) == 1200.0
    assert stage_seconds(deadline_at=3000.0, now=2000.0) == 1000.0


def test_a_stage_starts_with_exactly_one_minute_left_and_not_with_less() -> None:
    assert stage_seconds(deadline_at=60.0, now=0.0) == 60.0
    assert stage_seconds(deadline_at=59.9, now=0.0) is None
    assert stage_seconds(deadline_at=100.0, now=100.0) is None


@pytest.mark.parametrize(
    ("today", "expected"),
    [(date(2026, 11, 20), 11), (date(2026, 11, 30), 1), (date(2026, 12, 1), 31), (date(2028, 2, 29), 1)],
)
def test_days_left_counts_today_to_the_end_of_the_month(today: date, expected: int) -> None:
    assert days_left(today) == expected
