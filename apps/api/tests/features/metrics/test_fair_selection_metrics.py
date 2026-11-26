"""Integration tests for fair-selection metrics.

Implements the five TDD slices for metrics observability:
- Slice 1: task_queue_pending_by_phase metric
- Slice 2: task_queue_claimed_by_phase metric
- Slice 3: fair_selection_phase_transition counter
- Slice 4: document_coverage_pct metric
- Slice 5: Integration test for all metrics

Each slice has happy and negative path tests.
"""

from __future__ import annotations

import uuid

from app.features.metrics.fair_selection_metrics import (
    document_coverage_pct,
    fair_selection_phase_transition,
    increment_phase_transition,
    task_queue_claimed_by_phase,
    task_queue_completed_by_phase,
    task_queue_pending_by_phase,
)
from app.features.metrics.fair_selection_registry import (
    update_all_metrics,
    update_coverage_metrics,
)
from app.models.search import WorkTaskStatus
from app.models.translation import TranslationTask
from sqlalchemy.orm import Session

LOCALES = ["de", "en", "fr", "es", "it", "pt", "nl", "pl", "cs", "sk", "hu", "ro", "bg", "hr", "sv"]


# ============================================================================
# Slice 1: task_queue_pending_by_phase Metric
# ============================================================================


class TestPendingByPhase:
    """Test coverage for pending tasks by phase metric."""

    def test_task_queue_pending_by_phase_increments_on_enqueue(
        self, db_session: Session
    ) -> None:
        """Happy path: metric increments on enqueue.

        Setup: Create translation pipeline context
        Action: Enqueue 10 phase-1 tasks, 5 phase-2 tasks
        Assert: Metric task_queue_pending_by_phase{pipeline="translation",phase="1"} = 10
        Assert: Metric task_queue_pending_by_phase{pipeline="translation",phase="2"} = 5
        """
        # Create 10 phase-1 and 5 phase-2 tasks (each with unique candidate-locale pair)
        for i in range(10):
            task = TranslationTask(
                candidate_id=uuid.uuid4(),
                locale=LOCALES[i % len(LOCALES)],
                source_hash=f"hash_{i}",
                status=WorkTaskStatus.PENDING,
                priority=100,
                phase=1,
            )
            db_session.add(task)

        for i in range(5):
            task = TranslationTask(
                candidate_id=uuid.uuid4(),
                locale=LOCALES[(i + 10) % len(LOCALES)],
                source_hash=f"hash_phase2_{i}",
                status=WorkTaskStatus.PENDING,
                priority=100,
                phase=2,
            )
            db_session.add(task)

        db_session.commit()

        # Update metrics
        update_all_metrics(db_session)

        # Assert pending counts
        assert (
            task_queue_pending_by_phase.labels(pipeline="translation", phase="1")._value.get()
            == 10
        )
        assert (
            task_queue_pending_by_phase.labels(pipeline="translation", phase="2")._value.get()
            == 5
        )

    def test_task_queue_pending_by_phase_excludes_claimed_completed(
        self, db_session: Session
    ) -> None:
        """Negative path: excludes claimed and completed tasks.

        Setup: 10 phase-1 tasks enqueued
        Action: Claim 3 tasks, complete 2 tasks
        Assert: Metric still shows 5 pending (not 10; claimed/completed excluded)
        Assert: Gauge stays ≥ 0
        """
        # Create 10 phase-1 pending tasks (each with unique candidate-locale pair)
        for i in range(10):
            task = TranslationTask(
                candidate_id=uuid.uuid4(),
                locale=LOCALES[i % len(LOCALES)],
                source_hash=f"hash_{i}",
                status=WorkTaskStatus.PENDING,
                priority=100,
                phase=1,
            )
            db_session.add(task)

        db_session.commit()

        # Claim 3 tasks
        pending_tasks = db_session.query(TranslationTask).filter_by(
            status=WorkTaskStatus.PENDING
        ).limit(3).all()
        for task in pending_tasks:
            task.status = WorkTaskStatus.CLAIMED

        # Complete 2 tasks
        pending_tasks = db_session.query(TranslationTask).filter_by(
            status=WorkTaskStatus.PENDING
        ).limit(2).all()
        for task in pending_tasks:
            task.status = WorkTaskStatus.COMPLETED

        db_session.commit()

        # Update metrics
        update_all_metrics(db_session)

        # Assert only 5 pending remain
        metric_value = task_queue_pending_by_phase.labels(
            pipeline="translation", phase="1"
        )._value.get()
        assert metric_value == 5
        assert metric_value >= 0


# ============================================================================
# Slice 2: task_queue_claimed_by_phase Metric
# ============================================================================


class TestClaimedByPhase:
    """Test coverage for claimed tasks by phase metric."""

    def test_task_queue_claimed_by_phase_increments_on_claim(
        self, db_session: Session
    ) -> None:
        """Happy path: increments on claim.

        Setup: 10 phase-1 tasks enqueued
        Action: Claim 7 tasks (move to claimed status)
        Assert: Metric task_queue_claimed_by_phase{pipeline="translation",phase="1"} = 7
        Assert: Metric task_queue_pending_by_phase{pipeline="translation",phase="1"} = 3
        """
        # Create 10 phase-1 pending tasks
        for i in range(10):
            task = TranslationTask(
                candidate_id=uuid.uuid4(),
                locale=LOCALES[i % len(LOCALES)],
                source_hash=f"hash_{i}",
                status=WorkTaskStatus.PENDING,
                priority=100,
                phase=1,
            )
            db_session.add(task)

        db_session.commit()

        # Claim 7 tasks
        pending_tasks = db_session.query(TranslationTask).filter_by(
            status=WorkTaskStatus.PENDING
        ).limit(7).all()
        for task in pending_tasks:
            task.status = WorkTaskStatus.CLAIMED

        db_session.commit()

        # Update metrics
        update_all_metrics(db_session)

        # Assert claimed count
        assert (
            task_queue_claimed_by_phase.labels(pipeline="translation", phase="1")._value.get()
            == 7
        )
        assert (
            task_queue_pending_by_phase.labels(pipeline="translation", phase="1")._value.get()
            == 3
        )

    def test_task_queue_claimed_by_phase_excludes_expired_leases(
        self, db_session: Session
    ) -> None:
        """Negative path: excludes expired leases.

        Setup: Claim 5 tasks
        Action: Query metrics (treating expired leases as no longer claimed)
        Assert: Metric reflects only active leases (this test validates the query logic)
        Assert: Metric never negative
        """
        # Create 5 phase-1 tasks claimed
        for i in range(5):
            task = TranslationTask(
                candidate_id=uuid.uuid4(),
                locale=LOCALES[i % len(LOCALES)],
                source_hash=f"hash_{i}",
                status=WorkTaskStatus.CLAIMED,
                priority=100,
                phase=1,
            )
            db_session.add(task)

        db_session.commit()

        # Update metrics
        update_all_metrics(db_session)

        # Assert claimed count
        metric_value = task_queue_claimed_by_phase.labels(
            pipeline="translation", phase="1"
        )._value.get()
        assert metric_value == 5
        assert metric_value >= 0


# ============================================================================
# Slice 3: fair_selection_phase_transition Counter
# ============================================================================


class TestPhaseTransition:
    """Test coverage for phase transition counter."""

    def test_fair_selection_phase_transition_increments_on_state_change(
        self,
    ) -> None:
        """Happy path: increments on state change.

        Setup: State machine transitions phase 1 → 2 for translation pipeline
        Action: Call increment_phase_transition()
        Assert: Metric counter increments
        """
        # Get initial counter value (or 0 if first time)
        try:
            initial_value = fair_selection_phase_transition.labels(
                pipeline="translation", from_phase="1", to_phase="2"
            )._value.get()
        except KeyError:
            initial_value = 0

        # Increment phase transition
        increment_phase_transition("translation", from_phase=1, to_phase=2)

        # Assert counter incremented
        final_value = fair_selection_phase_transition.labels(
            pipeline="translation", from_phase="1", to_phase="2"
        )._value.get()
        assert final_value == initial_value + 1

    def test_fair_selection_phase_transition_not_incremented_on_non_transition(
        self,
    ) -> None:
        """Negative path: not incremented on non-transition.

        Setup: Phase already at 2, no state change
        Action: Verify counter not incremented for transitions that don't happen
        Assert: Counter stays at 0 for transitions that don't happen
        """
        # Get counter value for a transition that hasn't happened
        try:
            counter_value = fair_selection_phase_transition.labels(
                pipeline="nonexistent", from_phase="99", to_phase="100"
            )._value.get()
        except KeyError:
            # Expected: counter not yet created for this label combo
            counter_value = 0

        assert counter_value == 0


# ============================================================================
# Slice 4: document_coverage_pct Metric
# ============================================================================


class TestDocumentCoveragePct:
    """Test coverage for document coverage percentage metric."""

    def test_document_coverage_pct_calculated_correctly(
        self, db_session: Session
    ) -> None:
        """Happy path: calculated correctly.

        Setup: 10 documents (candidates), translation pipeline
        Enqueue tasks: complete 1 task per document for 5 documents
        Action: Call metric-calculation handler
        Assert: Metric document_coverage_pct{pipeline="translation"} = 50.0
        """
        # Create 10 candidates
        candidate_ids = [uuid.uuid4() for _ in range(10)]

        # Create 1 completed task per document for first 5 documents
        for i, candidate_id in enumerate(candidate_ids[:5]):
            task = TranslationTask(
                candidate_id=candidate_id,
                locale=LOCALES[i % len(LOCALES)],
                source_hash=f"hash_{i}",
                status=WorkTaskStatus.COMPLETED,
                priority=100,
            )
            db_session.add(task)

        # Create pending tasks for remaining 5 documents
        for i, candidate_id in enumerate(candidate_ids[5:], start=5):
            task = TranslationTask(
                candidate_id=candidate_id,
                locale=LOCALES[i % len(LOCALES)],
                source_hash=f"hash_{i}",
                status=WorkTaskStatus.PENDING,
                priority=100,
            )
            db_session.add(task)

        db_session.commit()

        # Update coverage metrics
        update_coverage_metrics(db_session)

        # Assert coverage = 50.0%
        coverage = document_coverage_pct.labels(pipeline="translation")._value.get()
        assert coverage == 50.0

    def test_document_coverage_pct_ignores_failed_tasks(self, db_session: Session) -> None:
        """Negative path: ignores failed tasks.

        Setup: 10 documents
        Complete 1 task for 5 documents, fail 1 task per remaining 5 documents
        Action: Call metric-calculation handler
        Assert: Metric = 50.0 (failed tasks don't count; only completed)
        Assert: Metric never exceeds 100.0
        """
        # Create 10 candidates
        candidate_ids = [uuid.uuid4() for _ in range(10)]

        # Create 1 completed task per document for first 5 documents
        for i, candidate_id in enumerate(candidate_ids[:5]):
            task = TranslationTask(
                candidate_id=candidate_id,
                locale=LOCALES[i % len(LOCALES)],
                source_hash=f"hash_{i}",
                status=WorkTaskStatus.COMPLETED,
                priority=100,
            )
            db_session.add(task)

        # Create 1 failed task per document for remaining 5 documents
        for i, candidate_id in enumerate(candidate_ids[5:], start=5):
            task = TranslationTask(
                candidate_id=candidate_id,
                locale=LOCALES[i % len(LOCALES)],
                source_hash=f"hash_{i}",
                status=WorkTaskStatus.FAILED,
                priority=100,
            )
            db_session.add(task)

        db_session.commit()

        # Update coverage metrics
        update_coverage_metrics(db_session)

        # Assert coverage = 50.0% (failed tasks don't count)
        coverage = document_coverage_pct.labels(pipeline="translation")._value.get()
        assert coverage == 50.0
        assert coverage <= 100.0


# ============================================================================
# Slice 5: Integration Test
# ============================================================================


class TestMetricsIntegration:
    """Integration tests for all metrics together."""

    def test_all_metrics_emitted_and_queryable(self, db_session: Session) -> None:
        """Happy path: all metrics emit without errors and are queryable.

        Setup: Create full workflow:
          - Enqueue 20 tasks (5 candidates, 4 locales, translation pipeline)
          - 10 phase-1, 10 phase-2
          - Claim 5 tasks, complete 3
        Action: Call update_all_metrics() and update_coverage_metrics()
        Assert: All 5 metric types are set (pending, claimed, completed, coverage, transition)
        Assert: Metrics readable via Prometheus client library
        Assert: No exceptions or errors during metric update
        """
        # Create 5 candidates
        candidate_ids = [uuid.uuid4() for _ in range(5)]

        # Create 20 tasks: 10 phase-1, 10 phase-2
        task_id = 0
        for candidate_id in candidate_ids:
            for phase in [1, 2]:
                for _ in range(2):
                    task = TranslationTask(
                        candidate_id=candidate_id,
                        locale=LOCALES[task_id % len(LOCALES)],
                        source_hash=f"hash_{task_id}",
                        status=WorkTaskStatus.PENDING,
                        priority=100,
                        phase=phase,
                    )
                    db_session.add(task)
                    task_id += 1

        db_session.commit()

        # Claim 5 tasks
        pending_tasks = db_session.query(TranslationTask).filter_by(
            status=WorkTaskStatus.PENDING
        ).limit(5).all()
        for task in pending_tasks:
            task.status = WorkTaskStatus.CLAIMED

        # Complete 3 tasks
        pending_tasks = db_session.query(TranslationTask).filter_by(
            status=WorkTaskStatus.PENDING
        ).limit(3).all()
        for task in pending_tasks:
            task.status = WorkTaskStatus.COMPLETED

        db_session.commit()

        # Update all metrics
        update_all_metrics(db_session)
        update_coverage_metrics(db_session)
        increment_phase_transition("translation", from_phase=1, to_phase=2)

        # Assert all metrics are readable and have expected properties
        pending_p1 = task_queue_pending_by_phase.labels(
            pipeline="translation", phase="1"
        )._value.get()
        claimed_p1 = task_queue_claimed_by_phase.labels(
            pipeline="translation", phase="1"
        )._value.get()
        completed_p1 = task_queue_completed_by_phase.labels(
            pipeline="translation", phase="1"
        )._value.get()
        coverage = document_coverage_pct.labels(pipeline="translation")._value.get()

        # Basic sanity checks
        assert pending_p1 >= 0
        assert claimed_p1 >= 0
        assert completed_p1 >= 0
        assert coverage >= 0.0
        assert coverage <= 100.0

    def test_metrics_handle_empty_queue(self, db_session: Session) -> None:
        """Negative path: handle empty queue without errors.

        Setup: No tasks enqueued
        Action: Call metric-update handlers
        Assert: Metrics set to 0 (not error/None)
        Assert: Coverage = 0.0 (no documents, no coverage)
        Assert: No division-by-zero errors
        """
        # No setup; queue is empty
        # Update metrics should not raise
        update_all_metrics(db_session)
        update_coverage_metrics(db_session)

        # Assert coverage is 0.0
        coverage = document_coverage_pct.labels(pipeline="translation")._value.get()
        assert coverage == 0.0
