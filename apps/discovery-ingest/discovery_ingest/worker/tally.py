"""Per-outcome counters for one drain."""

from __future__ import annotations

from dataclasses import dataclass

COMPLETED = "completed"
FAILED = "failed"
COMPLETED_RENDER_ENQUEUE_FAILED = "completed_render_enqueue_failed"
"""A fetch that completed but could not enqueue its follow-up ``render_page``: counted as both."""
COMPLETED_CAPTURE_ENQUEUE_FAILED = "completed_capture_enqueue_failed"
"""An extraction that completed but could not enqueue its ``capture_screenshot``: counted as both."""
STALE = "stale"
"""An embedding whose text changed while it was computed: the task is completed and the API queues the new text."""
REJECTED = "rejected"
"""A translation the API refused (a replayed complete, a human row, bounds): logged and counted as failed and rejected."""
UNAVAILABLE = "unavailable"
"""A translation the API could not store (object store down): the task was handed back, counted once."""
_COUNTERS = {
    COMPLETED: ("completed",),
    FAILED: ("failed",),
    COMPLETED_RENDER_ENQUEUE_FAILED: ("completed", "render_enqueue_failed"),
    COMPLETED_CAPTURE_ENQUEUE_FAILED: ("completed", "capture_enqueue_failed"),
    STALE: ("completed", "stale"),
    REJECTED: ("failed", "rejected"),
    UNAVAILABLE: ("unavailable",),
}


@dataclass(slots=True)
class Tally:
    """Mutable counters; its fields are a subset of :class:`DrainReport`'s."""

    batches: int = 0
    claimed: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    released: int = 0
    stale: int = 0
    rejected: int = 0
    unavailable: int = 0
    repaired: int = 0
    invalid: int = 0
    render_enqueue_failed: int = 0
    capture_enqueue_failed: int = 0
    llm_enqueue_failed: int = 0
    browser_seconds_used: float = 0.0
    neurons_used: float = 0.0
    llm_calls: int = 0
    ledger_unavailable: bool = False

    def record(self, outcome: str) -> None:
        """Count one task outcome label; an unknown label counts as skipped."""
        for name in _COUNTERS.get(outcome, ("skipped",)):
            setattr(self, name, getattr(self, name) + 1)
