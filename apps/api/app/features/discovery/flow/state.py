"""Classify one pipeline stage into a state: a pure function of its facts, its cadence and the thresholds.

The rules are one ordered list of ``(predicate, state)`` pairs. The first predicate that holds names the state; a stage
that matches none is ``idle``. Nothing here reads the database or the clock.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass

from app.features.discovery.flow.stage import Stage
from app.features.discovery.flow.thresholds import FlowThresholds

HOURS_PER_DAY = 24.0
BUDGET_STOPS = frozenset({"browser_budget", "browser_quota", "llm_budget", "llm_quota"})
"""Stop reasons that mean the stage spent its allotment, so more work waits for the next period."""
CLOCK_STOPS = frozenset({"time_budget", "rate_limited"})
"""Stop reasons that mean a run ended on the clock or a rate limit, while the allotment may still have room."""
QUEUE_EMPTY = "queue_empty"


class StageState(enum.StrEnum):
    """The state of one stage, in the order the rules test them."""

    DEAD = "dead"
    BUDGET_STOPPED = "budget_stopped"
    THROTTLED = "throttled"
    BLOCKED = "blocked"
    STARVED = "starved"
    OVERDUE = "overdue"
    BACKLOGGED = "backlogged"
    FLOWING = "flowing"
    IDLE = "idle"


@dataclass(frozen=True, slots=True)
class StageFacts:
    """What the state rules read about one stage at one instant."""

    has_producer: bool
    ready: int
    completed_24h: int
    failed_24h: int
    last_stop_reason: str | None
    last_run_age_hours: float | None
    upstream_overdue: bool
    has_headroom: bool
    allotment_full: bool

    @property
    def has_ready_work(self) -> bool:
        """Return whether the stage has ready tasks the next drain could claim."""
        return self.ready > 0


def run_overdue(age_hours: float | None, cadence_hours: float, thresholds: FlowThresholds) -> bool:
    """Return whether a last run older than ``age_hours`` is overdue for ``cadence_hours``; no run is never overdue."""
    return age_hours is not None and age_hours > thresholds.overdue_after_cadences * cadence_hours


@dataclass(frozen=True, slots=True)
class _Case:
    """One stage under judgement, with the cadence and thresholds it is measured against."""

    facts: StageFacts
    cadence_hours: float
    thresholds: FlowThresholds


def _no_producer(case: _Case) -> bool:
    return not case.facts.has_producer


def _budget_stopped(case: _Case) -> bool:
    facts = case.facts
    return facts.has_ready_work and (facts.last_stop_reason in BUDGET_STOPS or facts.allotment_full)


def _throttled(case: _Case) -> bool:
    facts = case.facts
    return facts.has_ready_work and facts.has_headroom and facts.last_stop_reason in CLOCK_STOPS


def _blocked(case: _Case) -> bool:
    return not case.facts.has_ready_work and case.facts.upstream_overdue


def _starved(case: _Case) -> bool:
    return not case.facts.has_ready_work and case.facts.last_stop_reason == QUEUE_EMPTY


def _overdue(case: _Case) -> bool:
    return run_overdue(case.facts.last_run_age_hours, case.cadence_hours, case.thresholds)


def _backlogged(case: _Case) -> bool:
    """Return whether clearing ``ready`` at the 24 h rate takes longer than the backlog limit of the cadence."""
    facts = case.facts
    limit_hours = case.thresholds.backlog_after_cadences * case.cadence_hours
    return facts.has_ready_work and HOURS_PER_DAY * facts.ready > limit_hours * facts.completed_24h


def _flowing(case: _Case) -> bool:
    return case.facts.completed_24h > 0


_RULES: tuple[tuple[Callable[[_Case], bool], StageState], ...] = (
    (_no_producer, StageState.DEAD),
    (_budget_stopped, StageState.BUDGET_STOPPED),
    (_throttled, StageState.THROTTLED),
    (_blocked, StageState.BLOCKED),
    (_starved, StageState.STARVED),
    (_overdue, StageState.OVERDUE),
    (_backlogged, StageState.BACKLOGGED),
    (_flowing, StageState.FLOWING),
)


def classify_stage(stage: Stage, facts: StageFacts, thresholds: FlowThresholds) -> StageState:
    """Return the state of ``stage`` given its ``facts``: the first rule that holds, else ``idle``."""
    case = _Case(facts, stage.cadence_hours, thresholds)
    return next((state for rule, state in _RULES if rule(case)), StageState.IDLE)
