"""Per-outcome counters for one drain."""

from __future__ import annotations

from dataclasses import dataclass

COMPLETED = "completed"
FAILED = "failed"
COMPLETED_RENDER_ENQUEUE_FAILED = "completed_render_enqueue_failed"
"""A fetch that completed but could not enqueue its follow-up ``render_page``: counted as both."""


@dataclass(slots=True)
class Tally:
    """Mutable counters; its fields are a subset of :class:`DrainReport`'s."""

    batches: int = 0
    claimed: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    released: int = 0
    render_enqueue_failed: int = 0
    browser_seconds_used: float = 0.0
    ledger_unavailable: bool = False

    def record(self, outcome: str) -> None:
        """Count one task outcome label; an unknown label counts as skipped."""
        if outcome == COMPLETED_RENDER_ENQUEUE_FAILED:
            self.completed += 1
            self.render_enqueue_failed += 1
        elif outcome == COMPLETED:
            self.completed += 1
        elif outcome == FAILED:
            self.failed += 1
        else:
            self.skipped += 1
