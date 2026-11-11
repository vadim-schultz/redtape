"""The loop every drain shares: run one batch at a time until a stop signal or a policy bound ends it."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from discovery_ingest.schemas import StopReason
from discovery_ingest.worker.batch import BatchResult
from discovery_ingest.worker.policy import DrainPolicy

BatchStep = Callable[[], BatchResult]
"""Claims and settles one batch, and reports its size and the stop signal that cut it short, if any."""


def monotonic() -> float:
    """Read the monotonic clock at call time, so a test that replaces ``time.monotonic`` is honoured."""
    return time.monotonic()


@dataclass(frozen=True, slots=True)
class Finish:
    """Why a drain ended and, for an ``error`` stop, the detail the report carries."""

    reason: StopReason
    error: str | None = None


def _finish(batch: BatchResult, policy: DrainPolicy, batches: int, elapsed: float) -> Finish | None:
    if batch.stop is not None:
        return Finish(batch.stop.reason, str(batch.stop) if batch.stop.reason == "error" else None)
    reason = policy.stop_reason(batches=batches, last_claimed=batch.size, elapsed=elapsed)
    return None if reason is None else Finish(reason)


def drain_until_stop(step: BatchStep, policy: DrainPolicy, clock: Callable[[], float]) -> Finish:
    """Run ``step`` until a stop reason appears; ``clock`` measures the time budget."""
    started, batches = clock(), 0
    while True:
        batches += 1
        finish = _finish(step(), policy, batches, clock() - started)
        if finish is not None:
            return finish
