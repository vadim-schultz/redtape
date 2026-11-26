"""Query and update fair-selection metrics: queue counts and coverage for every pipeline."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.features.fair_selection.pipelines import PIPELINE_TASKS, TaskModel
from app.features.metrics.fair_selection_metrics import (
    set_claimed_by_phase,
    set_completed_by_phase,
    set_coverage_pct,
    set_pending_by_phase,
)
from app.models.discovery.discovery_task import DiscoveryTask
from app.models.discovery.enums import DiscoveryTaskStatus
from app.models.search import WorkTaskStatus


def update_all_metrics(session: Session) -> None:
    """Refresh all queue metrics from current database state."""
    for pipeline in PIPELINE_TASKS:
        counts = _task_counts_by_status_and_phase(session, pipeline)
        for (status, phase), count in counts.items():
            if status == "pending":
                set_pending_by_phase(pipeline, phase, count)
            elif status == "claimed":
                set_claimed_by_phase(pipeline, phase, count)
            elif status == "completed":
                set_completed_by_phase(pipeline, phase, count)


def update_coverage_metrics(session: Session) -> None:
    """Calculate and set document coverage percentage per pipeline."""
    for pipeline in PIPELINE_TASKS:
        set_coverage_pct(pipeline, _calculate_coverage_pct(session, pipeline))


def _task_counts_by_status_and_phase(session: Session, pipeline: str) -> dict[tuple[str, int], int]:
    """Query task counts grouped by status and phase for a given pipeline."""
    task_model, _ = PIPELINE_TASKS[pipeline]
    return _query_task_counts(session, task_model)


def _query_task_counts(session: Session, task_model: TaskModel) -> dict[tuple[str, int], int]:
    """Query task counts for a specific task model."""
    stmt = select(task_model.status, task_model.phase, func.count()).group_by(task_model.status, task_model.phase)

    result = {}
    for status, phase, count in session.execute(stmt).all():
        # Normalize status to string value
        status_str = status.value if hasattr(status, "value") else str(status)
        result[(status_str, phase)] = int(count)

    return result


def _calculate_coverage_pct(session: Session, pipeline: str) -> float:
    """Return the percentage of a pipeline's entities with at least one completed task.

    An entity is a candidate for translation and embedding, and a catalogue page for snapshot translation and
    discovery. Every entity with any task in the pipeline counts toward the total, so a pending or failed task
    does not hide an uncovered entity.
    """
    task_model, entity_col = PIPELINE_TASKS[pipeline]
    total = _distinct_entities(session, entity_col)
    if total == 0:
        return 0.0
    covered = _distinct_entities(session, entity_col, task_model.status == _completed_status(task_model))
    return covered / total * 100.0


def _distinct_entities(session: Session, entity_col: InstrumentedAttribute[UUID], *where: ColumnElement[bool]) -> int:
    """Count the distinct entities in ``entity_col`` among the task rows that satisfy ``where``."""
    stmt = select(func.count(func.distinct(entity_col))).where(*where)
    return int(session.scalar(stmt) or 0)


def _completed_status(task_model: TaskModel) -> WorkTaskStatus | DiscoveryTaskStatus:
    """Return the status a completed task of ``task_model`` carries; discovery has its own status enum."""
    return DiscoveryTaskStatus.COMPLETED if task_model is DiscoveryTask else WorkTaskStatus.COMPLETED
