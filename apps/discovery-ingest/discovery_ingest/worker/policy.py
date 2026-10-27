"""Finite bounds that decide when a worker drain stops."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.schemas import BROWSER_TASK_KINDS, WORKER_DEFAULT_TASK_KINDS, DiscoveryTaskKind, StopReason

MAX_TASKS_PER_CLAIM = 50


@dataclass(frozen=True, slots=True)
class DrainPolicy:
    """Validated batch size, batch-count, wall-clock bounds and task kinds for one drain."""

    max_tasks: int = MAX_TASKS_PER_CLAIM
    max_batches: int = 1
    time_budget_seconds: float | None = None
    kinds: tuple[DiscoveryTaskKind, ...] = WORKER_DEFAULT_TASK_KINDS
    browser_budget_seconds: float | None = None

    def __post_init__(self) -> None:
        """Reject bounds that would make a drain empty or unbounded."""
        if not 1 <= self.max_tasks <= MAX_TASKS_PER_CLAIM:
            raise ValueError("max_tasks must be between 1 and 50")
        if self.max_batches < 1:
            raise ValueError("max_batches must be a positive integer")
        if self.time_budget_seconds is not None and self.time_budget_seconds <= 0:
            raise ValueError("time_budget_seconds must be positive")
        if not self.kinds:
            raise ValueError("kinds must name at least one task kind")
        if self.browser_budget_seconds is not None and self.browser_budget_seconds <= 0:
            raise ValueError("browser_budget_seconds must be positive")
        if self.drains_browser_kinds and self.browser_budget_seconds is None:
            raise ValueError("browser_budget_seconds is required when a browser kind is drained")

    @property
    def drains_browser_kinds(self) -> bool:
        """Whether any drained kind spends Cloudflare browser time."""
        return any(kind in BROWSER_TASK_KINDS for kind in self.kinds)

    def stop_reason(self, *, batches: int, last_claimed: int, elapsed: float) -> StopReason | None:
        """Return why the drain must stop after a batch, or ``None`` to continue."""
        if last_claimed == 0:
            return "queue_empty"
        if batches >= self.max_batches:
            return "batch_limit"
        if self.time_budget_seconds is not None and elapsed >= self.time_budget_seconds:
            return "time_budget"
        return None
