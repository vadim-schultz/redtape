"""The run's deadline: the Actions minutes this day may use, and each stage's share of the time left (pure arithmetic)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date

from discovery_ingest.operations.pipeline.stages import MIN_STAGE_SECONDS, STAGE_CAP_SECONDS

RUN_CEILING_SECONDS = 3600.0
"""Most time one daily run may take, so the job's own timeout is never the first limit to fire."""


def days_left(today: date) -> int:
    """Return the days from ``today`` to the end of its month, counting today."""
    return monthrange(today.year, today.month)[1] - today.day + 1


def run_seconds(actions_minutes_remaining: float, days: int) -> float:
    """Return the run's time: the Actions minutes left, spread evenly over the days left, capped at an hour."""
    spare = max(actions_minutes_remaining, 0.0)
    return min(spare * 60.0 / max(days, 1), RUN_CEILING_SECONDS)


def stage_seconds(deadline_at: float, now: float) -> float | None:
    """Return the time a stage may take from ``now``: the time left to the deadline, capped at 20 minutes.

    ``None`` when less than the minimum is left, so the stage is not started.
    """
    left = min(STAGE_CAP_SECONDS, deadline_at - now)
    return left if left >= MIN_STAGE_SECONDS else None
