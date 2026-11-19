"""The flow-graph thresholds: one table, first guesses that are tuned after a week of real data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FlowThresholds:
    """The multiples and the share that turn a cadence and an allotment into a stage state."""

    overdue_after_cadences: float = 1.5
    """A last run older than this many cadences is overdue."""
    backlog_after_cadences: float = 2.0
    """A queue that takes longer than this many cadences to clear at its 24 h rate is backlogged."""
    unused_headroom_share: float = 0.20
    """An allotment with more than this share of its cap left is unused headroom."""


DEFAULT_THRESHOLDS = FlowThresholds()
