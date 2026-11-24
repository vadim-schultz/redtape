"""The pipeline deadline: each stage gets the time left to the fixed ceiling, capped at twenty minutes (chapter 12)."""

from __future__ import annotations

from discovery_ingest.operations.pipeline import RUN_CEILING_SECONDS, stage_seconds


def test_the_run_ceiling_is_fixed_at_fifty_five_minutes_under_the_job_timeout() -> None:
    assert RUN_CEILING_SECONDS == 3300.0


def test_the_deadline_gives_each_stage_the_time_left_capped_at_twenty_minutes() -> None:
    assert stage_seconds(deadline_at=10_000.0, now=0.0) == 1200.0
    assert stage_seconds(deadline_at=3000.0, now=2000.0) == 1000.0


def test_the_deadline_starts_a_stage_only_with_a_minute_left() -> None:
    assert stage_seconds(deadline_at=60.0, now=0.0) == 60.0
    assert stage_seconds(deadline_at=59.9, now=0.0) is None
    assert stage_seconds(deadline_at=100.0, now=100.0) is None
