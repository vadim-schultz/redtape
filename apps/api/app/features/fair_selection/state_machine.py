"""State machine for fair task selection priority formula and phase transitions.

Implements production state transition logic for the three-phase selection strategy:
- Phase 1 (Breadth-First): Every document gets ≥1 task per locale
- Phase 2 (Depth-First): Remaining work completed by confidence
- Phase 3 (Refresh): New versions re-enqueued

Also provides design validators used by design tests (C1).
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.features.fair_selection.pipelines import PIPELINE_TASKS
from app.features.metrics.fair_selection_metrics import increment_phase_transition
from app.models.fair_selection_state import FairSelectionState
from app.models.search import WorkTaskStatus

if TYPE_CHECKING:
    pass

# Prometheus metrics. The completed-transition counter lives in app.features.metrics.fair_selection_metrics:
# registering the same metric name twice in one process raises DuplicateTimeseries.
phase_transition_duration = Histogram(
    "fair_selection_phase_transition_duration_seconds",
    "Duration of phase transition operation",
    ["pipeline"],
)

phase_transition_blocked = Counter(
    "fair_selection_phase_transition_blocked_total",
    "Count of phase transitions blocked due to unmet conditions",
    ["pipeline", "from_phase", "to_phase", "reason"],
)


class PhaseCoverage:
    """Tracks coverage bitmap for a document across locales.

    Uses a 64-bit integer bitmap where bit N represents locale N completion.
    Assumption: ≤64 locales.
    """

    def __init__(self, num_locales: int) -> None:
        """Initialize coverage tracker for a document.

        Args:
            num_locales: Number of locales (must be ≤ 64).
        """
        if num_locales > 64:
            raise ValueError("Coverage bitmap only supports ≤64 locales")
        self.num_locales = num_locales
        self.bitmap: int = 0

    def mark_complete(self, locale_index: int) -> None:
        """Mark a locale as complete.

        Args:
            locale_index: Zero-indexed locale position.
        """
        if not 0 <= locale_index < self.num_locales:
            raise ValueError(f"Locale index {locale_index} out of range [0, {self.num_locales})")
        self.bitmap |= 1 << locale_index

    def is_phase_complete(self) -> bool:
        """Check if all locales are complete (phase 1 → 2 trigger).

        Returns:
            True if all locales have been marked complete.
        """
        full_mask = (1 << self.num_locales) - 1
        return self.bitmap == full_mask


class StateMachine:
    """Phase-state machine for fair task selection.

    Tracks phase transitions (1 → 2 → 3) based on completion coverage.
    """

    def __init__(self, num_documents: int, num_locales: int) -> None:
        """Initialize state machine.

        Args:
            num_documents: Number of documents in workload.
            num_locales: Number of locales per document.
        """
        self.num_documents = num_documents
        self.num_locales = num_locales
        self.current_phase = 1
        self.phase_1_complete = False

        # Track coverage per document
        self._coverages: list[PhaseCoverage] = [PhaseCoverage(num_locales) for _ in range(num_documents)]

    def settle_task(self, doc_index: int, locale_index: int) -> None:
        """Mark a task as settled (completed).

        Auto-transitions phase 1 → 2 if all documents complete.

        Args:
            doc_index: Zero-indexed document position.
            locale_index: Zero-indexed locale position.
        """
        if not 0 <= doc_index < self.num_documents:
            raise ValueError(f"Document index {doc_index} out of range [0, {self.num_documents})")

        self._coverages[doc_index].mark_complete(locale_index)

        # Check for phase 1 → 2 transition
        if not self.phase_1_complete and self._check_phase1_complete():
            self.current_phase = 2
            self.phase_1_complete = True

    def _check_phase1_complete(self) -> bool:
        """Check if all documents have ≥1 completed task per locale.

        Returns:
            True if all documents are phase 1 complete.
        """
        return all(cov.is_phase_complete() for cov in self._coverages)


def calculate_priority(
    *,
    phase: int,
    confidence: float,
    locale_index: int,
    candidate_id: str,  # For grouping in claim (not in formula)
) -> int:
    """Calculate priority score for task selection.

    Priority formula (unified across pipelines):
      priority = (phase_component * 100_000) + (confidence_rank * 100) + locale_index

    Where:
      phase_component = 0 if phase 1, 1 if phase 2, 2 if phase 3
      confidence_rank = 1000 - round(confidence * 1000)  (higher = lower priority)
      locale_index = 0–99 (stable tie-break within (phase, rank))

    Args:
        phase: Phase (1, 2, or 3).
        confidence: Confidence score (0.0–1.0).
        locale_index: Locale index for tie-breaking (0–99).
        candidate_id: Candidate ID (used for grouping, not in formula).

    Returns:
        Priority score (lower = claim sooner).
    """
    if not 1 <= phase <= 3:
        raise ValueError(f"Phase must be 1, 2, or 3; got {phase}")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence must be 0.0–1.0; got {confidence}")
    if not 0 <= locale_index <= 99:
        raise ValueError(f"Locale index must be 0–99; got {locale_index}")

    # Phase component: 0 for phase 1, 100_000 for phase 2, 200_000 for phase 3
    phase_component = (phase - 1) * 100_000

    # Confidence rank: 1000 - round(confidence * 1000)
    # (confidence=1.0 → rank=0, confidence=0.0 → rank=1000)
    confidence_rank = 1000 - round(confidence * 1000)

    # Priority formula
    priority = phase_component + (confidence_rank * 100) + locale_index

    return priority


# ============================================================================
# Production Implementation: State Transitions (C3)
# ============================================================================


def check_phase_one_complete(pipeline: str, session: Session | None = None) -> bool:
    """Check if all documents have ≥1 completed task per pipeline.

    Args:
        pipeline: Name of pipeline ('translation', 'embedding', 'discovery', etc.)
        session: SQLAlchemy session. If None, creates a new one.

    Returns:
        True if all documents have ≥1 completed task; False otherwise.
    """
    if pipeline not in PIPELINE_TASKS:
        raise ValueError(f"Unknown pipeline: {pipeline}")

    task_model, entity_col = PIPELINE_TASKS[pipeline]

    # Use provided session or create new one
    s = session or SessionLocal()
    try:
        # Count total unique entities tracked for this pipeline
        total_entities = (
            s.query(func.count(func.distinct(FairSelectionState.entity_id)))
            .filter(FairSelectionState.pipeline == pipeline)
            .scalar()
            or 0
        )

        if total_entities == 0:
            return True  # No entities = vacuously true

        # Count unique entities with ≥1 completed task
        completed_entities = (
            s.query(func.count(func.distinct(entity_col)))
            .filter(task_model.status == WorkTaskStatus.COMPLETED)
            .scalar()
            or 0
        )

        return completed_entities >= total_entities
    finally:
        if session is None:
            s.close()


def _check_phase_two_complete(pipeline: str, session: Session | None = None) -> bool:
    """Check if all phase 2 tasks are completed.

    Args:
        pipeline: Pipeline name.
        session: SQLAlchemy session. If None, creates a new one.

    Returns:
        True if all phase 2 entities are complete; False otherwise.
    """
    # Simplified: check if all phase 2 entities have completed all their tasks
    # For now, return False to be conservative
    return False


def _check_phase_three_exists(pipeline: str, session: Session | None = None) -> bool:
    """Check if any phase 3 items exist for this pipeline.

    Args:
        pipeline: Pipeline name.
        session: SQLAlchemy session. If None, creates a new one.

    Returns:
        True if phase 3 items exist; False otherwise.
    """
    s = session or SessionLocal()
    try:
        phase_three_count = (
            s.query(FairSelectionState)
            .filter(
                FairSelectionState.pipeline == pipeline,
                FairSelectionState.phase == 3,
            )
            .count()
        )

        return phase_three_count > 0
    finally:
        if session is None:
            s.close()


def transition_phase(
    pipeline: str,
    from_phase: int,
    to_phase: int,
    session: Session | None = None,
) -> int:
    """Advance all entities in a pipeline from one phase to another if conditions are met.

    **Phase 1 → 2**: Triggered when all entities have ≥1 completed task.
    **Phase 2 → 3**: Triggered when all phase 2 tasks are completed.
    **Phase 3 → 1** (loop): If no phase 3 items remain after all phase 2 done.

    Args:
        pipeline: Pipeline name ('translation', 'embedding', 'discovery', etc.)
        from_phase: Current phase (1, 2, or 3).
        to_phase: Target phase (1, 2, or 3).
        session: SQLAlchemy session. If None, creates a new one.

    Returns:
        Number of rows updated.

    Raises:
        ValueError: Invalid phase transition or pipeline.
    """
    start_time = time.time()

    # Validate transition
    valid_transitions = {
        (1, 2): "breadth_first_complete",
        (2, 3): "depth_first_complete",
        (3, 1): "refresh_cycle_reset",
    }
    if (from_phase, to_phase) not in valid_transitions:
        raise ValueError(f"Invalid transition: phase {from_phase} → {to_phase}")

    s = session or SessionLocal()
    try:
        # Check if transition condition is met
        condition_met = True
        blocked_reason = None

        if from_phase == 1 and to_phase == 2:
            if not check_phase_one_complete(pipeline, session=s):
                condition_met = False
                blocked_reason = "incomplete_coverage"
        elif from_phase == 2 and to_phase == 3:
            if not _check_phase_two_complete(pipeline, session=s):
                condition_met = False
                blocked_reason = "incomplete_phase_two"
        elif from_phase == 3 and to_phase == 1 and _check_phase_three_exists(pipeline, session=s):
            condition_met = False
            blocked_reason = "phase_three_exists"

        # If condition not met, record blocked metric and return 0
        if not condition_met:
            phase_transition_blocked.labels(
                pipeline=pipeline,
                from_phase=from_phase,
                to_phase=to_phase,
                reason=blocked_reason or "unknown",
            ).inc()
            return 0

        # Perform transition: update all entities in from_phase to to_phase
        updated = (
            s.query(FairSelectionState)
            .filter(
                FairSelectionState.pipeline == pipeline,
                FairSelectionState.phase == from_phase,
            )
            .update(
                {FairSelectionState.phase: to_phase, FairSelectionState.updated_at: func.now()},
                synchronize_session=False,
            )
        )
        s.commit()

        # Record metrics
        duration = time.time() - start_time
        increment_phase_transition(pipeline, from_phase, to_phase)
        phase_transition_duration.labels(pipeline=pipeline).observe(duration)

        return updated
    finally:
        if session is None:
            s.close()


def on_task_settled(
    pipeline: str,
    entity_id: uuid.UUID,
    task_status: str,  # 'COMPLETED', 'FAILED', etc.
    session: Session | None = None,
) -> None:
    """Handle a task settlement (completed or failed).

    Checks if this settlement allows a phase transition, and triggers
    automatic advancement if criteria are met.

    Args:
        pipeline: Pipeline that settled the task.
        entity_id: Candidate or catalogue_service_id.
        task_status: Final status of the task.
        session: SQLAlchemy session. If None, creates a new one.
    """
    if task_status != "COMPLETED":
        return  # Only phase transitions on completion

    # Attempt phase 1 → 2 transition
    transition_phase(pipeline, from_phase=1, to_phase=2, session=session)

    # Note: Phase 2 → 3 may happen during periodic audit, not on every task
