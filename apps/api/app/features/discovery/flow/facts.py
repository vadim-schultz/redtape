"""The facts the state rules read, built from what the service read about a stage at one instant."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from app.features.discovery.budgets import BudgetStatus
from app.features.discovery.flow.queues import QueueFigures
from app.features.discovery.flow.reads import Intake, LastRun
from app.features.discovery.flow.stage import Stage
from app.features.discovery.flow.state import StageFacts, run_overdue
from app.features.discovery.flow.thresholds import FlowThresholds
from app.features.discovery.flow.topology import STAGE_BY_ID, upstream_ids

SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True, slots=True)
class StageReading:
    """What the service read about one stage: its queue, its intake, its run, its upstream and its allotment."""

    queue: QueueFigures
    intake: Intake
    last_run: LastRun | None
    upstream_overdue: bool
    allotment: BudgetStatus | None


def age_hours(run: LastRun | None, now: datetime) -> float | None:
    """Return how many hours ago ``run`` started, or ``None`` when no run is recorded."""
    return None if run is None else (now - run.started_at).total_seconds() / SECONDS_PER_HOUR


def upstream_overdue(stage: Stage, runs: Mapping[str, LastRun], now: datetime, thresholds: FlowThresholds) -> bool:
    """Return whether any stage that feeds ``stage`` has a last run overdue for that stage's own cadence."""
    return any(_overdue_upstream(STAGE_BY_ID[source], runs, now, thresholds) for source in upstream_ids(stage.id))


def _overdue_upstream(source: Stage, runs: Mapping[str, LastRun], now: datetime, thresholds: FlowThresholds) -> bool:
    run = runs.get(source.run_stage.value)
    return run_overdue(age_hours(run, now), source.cadence_hours, thresholds)


def stage_facts(reading: StageReading, now: datetime, thresholds: FlowThresholds) -> StageFacts:
    """Return the facts the state rules read for one stage, measured at ``now``."""
    return StageFacts(
        has_producer=reading.intake.total > 0,
        ready=reading.queue.ready,
        completed_24h=reading.queue.completed_24h,
        failed_24h=reading.queue.failed_24h,
        last_stop_reason=None if reading.last_run is None else reading.last_run.stop_reason,
        last_run_age_hours=age_hours(reading.last_run, now),
        upstream_overdue=reading.upstream_overdue,
        has_headroom=_has_headroom(reading.allotment, thresholds),
        allotment_full=_is_full(reading.allotment),
    )


def _has_headroom(allotment: BudgetStatus | None, thresholds: FlowThresholds) -> bool:
    if allotment is None or allotment.cap <= 0:
        return False
    return float(allotment.remaining) / allotment.cap > thresholds.unused_headroom_share


def _is_full(allotment: BudgetStatus | None) -> bool:
    return allotment is not None and (allotment.exhausted or allotment.remaining <= 0)
