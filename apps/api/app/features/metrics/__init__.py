"""Metrics module for observability."""

from __future__ import annotations

from app.features.metrics.fair_selection_metrics import (
    increment_phase_transition,
    set_claimed_by_phase,
    set_completed_by_phase,
    set_coverage_pct,
    set_pending_by_phase,
)

__all__ = [
    "set_pending_by_phase",
    "set_claimed_by_phase",
    "set_completed_by_phase",
    "increment_phase_transition",
    "set_coverage_pct",
]
