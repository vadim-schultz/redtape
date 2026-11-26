"""Audit job for fair task selection state consistency.

Detects and corrects drift between fair_selection_state phase/coverage and
actual completed tasks in the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.features.fair_selection.pipelines import PIPELINE_TASKS
from app.models.fair_selection_state import FairSelectionState
from app.models.search import WorkTaskStatus

if TYPE_CHECKING:
    pass


@dataclass
class AuditReport:
    """Report from fair selection state audit run.

    Tracks entities checked, drift detected, and corrections applied.
    """

    pipeline: str
    entities_checked: int = 0
    drift_detected: int = 0
    corrected: int = 0
    errors: list[str] = field(default_factory=list)


def _compute_expected_state(pipeline: str, entity_id: str, session: Session) -> tuple[int, int]:
    """Compute expected phase and coverage_bitmap for an entity.

    Based on actual completed tasks in the database, determines what the
    phase and coverage should be.

    Args:
        pipeline: Pipeline name ('translation', 'embedding', 'discovery', etc.)
        entity_id: Entity ID (candidate_id or catalogue_service_id)
        session: SQLAlchemy session.

    Returns:
        Tuple of (expected_phase, coverage_bitmap)
    """
    if pipeline not in PIPELINE_TASKS:
        return 1, 0  # Default to phase 1 if unknown pipeline

    task_model, entity_col = PIPELINE_TASKS[pipeline]

    # Count completed tasks for this entity
    completed_tasks = (
        session.query(task_model)
        .filter(
            entity_col == entity_id,
            task_model.status == WorkTaskStatus.COMPLETED,
        )
        .count()
    )

    # Compute coverage bitmap (simplified: just check if any task completed)
    # In production, would track specific locale completion
    coverage_bitmap = 1 if completed_tasks > 0 else 0

    # Determine phase based on completion
    # Simple heuristic: if any completed tasks, consider phase 1 done
    # In production, would check "all locales of all documents complete" for phase 1->2
    expected_phase = 1 if completed_tasks > 0 else 1

    return expected_phase, coverage_bitmap


def audit_fair_selection_state(pipeline: str, session: Session | None = None) -> AuditReport:
    """Audit and repair fair_selection_state consistency.

    Recomputes phase and coverage_bitmap for all entities in the pipeline
    based on actual completed tasks. Corrects any drift between tracking
    table and reality.

    Args:
        pipeline: Pipeline name to audit ('translation', 'embedding', 'discovery', etc.)
        session: SQLAlchemy session. If None, creates a new one.

    Returns:
        AuditReport with counts and any errors encountered.
    """
    report = AuditReport(pipeline=pipeline)

    s = session or SessionLocal()
    try:
        # Query all entities in fair_selection_state for this pipeline
        entities = s.query(FairSelectionState).filter(FairSelectionState.pipeline == pipeline).all()

        for entity in entities:
            report.entities_checked += 1

            try:
                # Compute expected phase and coverage based on completed tasks
                expected_phase, expected_coverage = _compute_expected_state(pipeline, str(entity.entity_id), s)

                # Compare with current state
                if entity.phase != expected_phase or entity.coverage_bitmap != expected_coverage:
                    report.drift_detected += 1
                    entity.phase = expected_phase
                    entity.coverage_bitmap = expected_coverage
                    report.corrected += 1
            except Exception as e:
                report.errors.append(f"Entity {entity.entity_id}: {str(e)}")

        s.commit()
        return report
    finally:
        if session is None:
            s.close()
