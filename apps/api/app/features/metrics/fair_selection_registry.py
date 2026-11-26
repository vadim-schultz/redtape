"""Query and update fair-selection metrics."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.features.metrics.fair_selection_metrics import (
    set_claimed_by_phase,
    set_completed_by_phase,
    set_coverage_pct,
    set_pending_by_phase,
)
from app.models.discovery.discovery_task import DiscoveryTask
from app.models.discovery.enums import DiscoveryTaskStatus
from app.models.search import EmbeddingTask, WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslationTask
from app.models.translation import TranslationTask


def update_all_metrics(session: Session) -> None:
    """Refresh all queue metrics from current database state."""
    for pipeline in ["translation", "snapshot_translation", "embedding", "discovery"]:
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
    for pipeline in ["translation", "snapshot_translation", "embedding", "discovery"]:
        pct = _calculate_coverage_pct(session, pipeline)
        set_coverage_pct(pipeline, pct)


def _task_counts_by_status_and_phase(
    session: Session, pipeline: str
) -> dict[tuple[str, int], int]:
    """Query task counts grouped by status and phase for a given pipeline."""
    if pipeline == "translation":
        task_model: Any = TranslationTask
    elif pipeline == "snapshot_translation":
        task_model = SnapshotTranslationTask
    elif pipeline == "embedding":
        task_model = EmbeddingTask
    elif pipeline == "discovery":
        task_model = DiscoveryTask
    else:
        return {}

    stmt = (
        select(task_model.status, task_model.phase, func.count())
        .group_by(task_model.status, task_model.phase)
    )

    result = {}
    for status, phase, count in session.execute(stmt).all():
        # Normalize status to string value
        status_str = status.value if hasattr(status, "value") else str(status)
        result[(status_str, phase)] = int(count)

    return result


def _calculate_coverage_pct(session: Session, pipeline: str) -> float:
    """Calculate percentage of documents with ≥1 completed task.

    For translation: document = candidate; for discovery: document = catalogue_service.
    """
    if pipeline == "translation":
        # Count distinct candidates with ≥1 completed task
        stmt_total = select(
            func.count(func.distinct(TranslationTask.candidate_id))
        ).where(TranslationTask.status == WorkTaskStatus.COMPLETED)
        stmt_covered = select(
            func.count(func.distinct(TranslationTask.candidate_id))
        ).where(TranslationTask.status == WorkTaskStatus.COMPLETED)

        total_count = int(session.scalar(stmt_total) or 0)
        covered_count = int(session.scalar(stmt_covered) or 0)
    elif pipeline == "snapshot_translation":
        stmt_total = select(
            func.count(func.distinct(SnapshotTranslationTask.catalogue_service_id))
        ).where(SnapshotTranslationTask.status == WorkTaskStatus.COMPLETED)
        stmt_covered = select(
            func.count(func.distinct(SnapshotTranslationTask.catalogue_service_id))
        ).where(SnapshotTranslationTask.status == WorkTaskStatus.COMPLETED)

        total_count = int(session.scalar(stmt_total) or 0)
        covered_count = int(session.scalar(stmt_covered) or 0)
    elif pipeline == "embedding":
        stmt_total = select(
            func.count(func.distinct(EmbeddingTask.candidate_id))
        ).where(EmbeddingTask.status == WorkTaskStatus.COMPLETED)
        stmt_covered = select(
            func.count(func.distinct(EmbeddingTask.candidate_id))
        ).where(EmbeddingTask.status == WorkTaskStatus.COMPLETED)

        total_count = int(session.scalar(stmt_total) or 0)
        covered_count = int(session.scalar(stmt_covered) or 0)
    elif pipeline == "discovery":
        stmt_total = select(
            func.count(func.distinct(DiscoveryTask.catalogue_service_id))
        ).where(DiscoveryTask.status == DiscoveryTaskStatus.COMPLETED)
        stmt_covered = select(
            func.count(func.distinct(DiscoveryTask.catalogue_service_id))
        ).where(DiscoveryTask.status == DiscoveryTaskStatus.COMPLETED)

        total_count = int(session.scalar(stmt_total) or 0)
        covered_count = int(session.scalar(stmt_covered) or 0)
    else:
        return 0.0

    if total_count == 0:
        return 0.0

    return (covered_count / total_count) * 100.0
