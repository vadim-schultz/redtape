"""The run's clock: one fixed ceiling for the whole run, and each stage's share of the time that is left (pure arithmetic)."""

from __future__ import annotations

RUN_CEILING_SECONDS = 3300.0
"""Most time one daily run may take: 55 minutes, under the job's 60-minute timeout, which is the backstop."""
STAGE_CAP_SECONDS = 1200.0
"""Most time one stage may take in one phase: 20 minutes."""
MIN_STAGE_SECONDS = 60.0
"""Least time a stage is started with; with less left, the stage is not started."""


def stage_seconds(deadline_at: float, now: float) -> float | None:
    """Return the time a stage may take from ``now``: the time left to the deadline, capped at 20 minutes.

    ``None`` when less than the minimum is left, so the stage is not started.
    """
    left = min(STAGE_CAP_SECONDS, deadline_at - now)
    return left if left >= MIN_STAGE_SECONDS else None
