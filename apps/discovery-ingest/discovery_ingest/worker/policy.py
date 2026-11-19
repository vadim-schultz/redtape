"""Finite bounds that decide when a worker drain stops."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.schemas import (
    BROWSER_TASK_KINDS,
    LLM_TASK_KINDS,
    WORKER_DEFAULT_TASK_KINDS,
    DiscoveryTaskKind,
    StopReason,
)

MAX_TASKS_PER_CLAIM = 50
MAX_CONCURRENCY = 4
"""The most engine calls one drain may have in flight; an engine may allow fewer (its own ``CallLimits``)."""
MAX_LLM_CONCURRENCY = 8
"""The most model calls one llm_extract drain may have in flight (chapter 5); the neuron meter still bounds the spend."""


@dataclass(frozen=True, slots=True)
class DrainPolicy:
    """Validated batch size, batch-count, wall-clock bounds, task kinds and call concurrency for one drain."""

    max_tasks: int = MAX_TASKS_PER_CLAIM
    max_batches: int = 1
    time_budget_seconds: float | None = None
    kinds: tuple[DiscoveryTaskKind, ...] = WORKER_DEFAULT_TASK_KINDS
    browser_budget_seconds: float | None = None
    neuron_budget: float | None = None
    concurrency: int = 1

    def __post_init__(self) -> None:
        """Reject bounds that would make a drain empty or unbounded."""
        self._check_batches()
        self._check_browser_budget()
        self._check_neuron_budget()
        self._check_concurrency()

    def _check_concurrency(self) -> None:
        cap = MAX_LLM_CONCURRENCY if self.drains_llm_kinds else MAX_CONCURRENCY
        if not 1 <= self.concurrency <= cap:
            raise ValueError(f"concurrency must be between 1 and {cap}")

    def _check_batches(self) -> None:
        if not 1 <= self.max_tasks <= MAX_TASKS_PER_CLAIM:
            raise ValueError("max_tasks must be between 1 and 50")
        if self.max_batches < 1:
            raise ValueError("max_batches must be a positive integer")
        if self.time_budget_seconds is not None and self.time_budget_seconds <= 0:
            raise ValueError("time_budget_seconds must be positive")
        if not self.kinds:
            raise ValueError("kinds must name at least one task kind")

    def _check_browser_budget(self) -> None:
        if self.browser_budget_seconds is not None and self.browser_budget_seconds <= 0:
            raise ValueError("browser_budget_seconds must be positive")
        if self.drains_browser_kinds and self.browser_budget_seconds is None:
            raise ValueError("browser_budget_seconds is required when a browser kind is drained")

    def _check_neuron_budget(self) -> None:
        if self.neuron_budget is not None and self.neuron_budget <= 0:
            raise ValueError("neuron_budget must be positive")
        if self.drains_llm_kinds and self.neuron_budget is None:
            raise ValueError("neuron_budget is required when llm_extract is drained")

    @property
    def drains_browser_kinds(self) -> bool:
        """Whether any drained kind spends Cloudflare browser time."""
        return any(kind in BROWSER_TASK_KINDS for kind in self.kinds)

    @property
    def drains_llm_kinds(self) -> bool:
        """Whether any drained kind spends Workers AI neurons."""
        return any(kind in LLM_TASK_KINDS for kind in self.kinds)

    def stop_reason(self, *, batches: int, last_claimed: int, elapsed: float) -> StopReason | None:
        """Return why the drain must stop after a batch, or ``None`` to continue."""
        if last_claimed == 0:
            return "queue_empty"
        if batches >= self.max_batches:
            return "batch_limit"
        if self.time_budget_seconds is not None and elapsed >= self.time_budget_seconds:
            return "time_budget"
        return None
