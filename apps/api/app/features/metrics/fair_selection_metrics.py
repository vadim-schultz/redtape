"""Prometheus metrics for fair-selection queue observability."""

from __future__ import annotations

from prometheus_client import Counter, Gauge

task_queue_pending_by_phase = Gauge(
    "task_queue_pending_by_phase",
    "Number of pending tasks grouped by phase and pipeline",
    labelnames=["pipeline", "phase"],
)

task_queue_claimed_by_phase = Gauge(
    "task_queue_claimed_by_phase",
    "Number of claimed tasks grouped by phase and pipeline",
    labelnames=["pipeline", "phase"],
)

task_queue_completed_by_phase = Gauge(
    "task_queue_completed_by_phase",
    "Number of completed tasks grouped by phase and pipeline",
    labelnames=["pipeline", "phase"],
)

fair_selection_phase_transition = Counter(
    "fair_selection_phase_transition_total",
    "Count of phase transitions (auto-triggered or manual)",
    labelnames=["pipeline", "from_phase", "to_phase"],
)

document_coverage_pct = Gauge(
    "document_coverage_pct",
    "Percentage of documents with ≥1 completed task per pipeline",
    labelnames=["pipeline"],
)


def set_pending_by_phase(pipeline: str, phase: int, count: int) -> None:
    """Set pending task count for a phase and pipeline."""
    task_queue_pending_by_phase.labels(pipeline=pipeline, phase=str(phase)).set(count)


def set_claimed_by_phase(pipeline: str, phase: int, count: int) -> None:
    """Set claimed task count for a phase and pipeline."""
    task_queue_claimed_by_phase.labels(pipeline=pipeline, phase=str(phase)).set(count)


def set_completed_by_phase(pipeline: str, phase: int, count: int) -> None:
    """Set completed task count for a phase and pipeline."""
    task_queue_completed_by_phase.labels(pipeline=pipeline, phase=str(phase)).set(count)


def increment_phase_transition(pipeline: str, from_phase: int, to_phase: int) -> None:
    """Increment counter for a phase transition."""
    fair_selection_phase_transition.labels(pipeline=pipeline, from_phase=str(from_phase), to_phase=str(to_phase)).inc()


def set_coverage_pct(pipeline: str, pct: float) -> None:
    """Set coverage percentage for a pipeline."""
    document_coverage_pct.labels(pipeline=pipeline).set(pct)
