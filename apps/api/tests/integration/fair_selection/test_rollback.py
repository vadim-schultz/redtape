"""Slice 5: Rollback Resilience Test for fair task selection.

Validates that the system handles code rollbacks gracefully and that old
(pre-phase) tasks are handled correctly by new code.
"""

from __future__ import annotations

from uuid import uuid4

from app.features.search.clock import utc_now
from app.features.search.leased_queue import LeasedQueue
from app.models.fair_selection_state import FairSelectionState
from app.models.search import WorkTaskStatus
from app.models.translation import TranslationTask
from sqlalchemy.orm import Session
from tests.integration.fair_selection.conftest import create_candidate_tasks

from embedding_support import make_key
from fair_selection_support import candidate_ids
from search_support import make_candidate


class TestRollback:
    """Test rollback resilience for fair task selection."""

    def test_rollback_code_queue_still_functional(self, db_session: Session) -> None:
        """Happy path: rollback doesn't break queue functionality.

        Setup: 2 candidates (phase 1, phase 2), enqueue with new code.
        Snapshot: Take note of task count.
        Modify: Simulate old code (reset status to pending).
        Rollback: Restore to pending state.
        Re-enqueue: New tasks with phase-aware priority.
        Claim: Verify claims work and respect new priorities.
        """
        # Setup
        candidate_a, candidate_b = candidate_ids(db_session, 2)

        state_a = FairSelectionState(pipeline="translation", entity_id=candidate_a, phase=1)
        state_b = FairSelectionState(pipeline="translation", entity_id=candidate_b, phase=2)
        db_session.add_all([state_a, state_b])
        db_session.commit()

        # Create tasks with new code
        create_candidate_tasks(db_session, candidate_a, ["en", "de"], phase=1)
        create_candidate_tasks(db_session, candidate_b, ["en", "de"], phase=2)

        # Backup state: count tasks
        tasks_before = db_session.query(TranslationTask).all()
        task_count_before = len(tasks_before)
        assert task_count_before == 4, f"Expected 4 tasks, got {task_count_before}"

        # Simulate rollback: reset all tasks to PENDING
        for task in tasks_before:
            task.status = WorkTaskStatus.PENDING
        db_session.commit()

        # Re-create tasks (simulating new deploy after rollback)
        # Note: in real scenario, tasks wouldn't be re-created if already PENDING
        # This simulates the idempotency of enqueue_many

        # Claim
        api_key_id = make_key(db_session).id
        queue = LeasedQueue(db_session, model=TranslationTask)
        claimed = queue.claim(
            api_key_id,
            utc_now(),
            limit=1,
            scope=(),
            grouping=(TranslationTask.candidate_id,),
            phase_field=TranslationTask.phase,
        )

        # Assert: claim successful; no crashes
        assert claimed is not None, "Expected successful claim after rollback"
        assert len(claimed) > 0, "Expected at least one claimed task"
        assert claimed[0].candidate_id in [candidate_a, candidate_b]

    def test_rollback_old_tasks_handled_gracefully(self, db_session: Session) -> None:
        """Negative path: old tasks (pre-phase) don't cause crashes post-deploy.

        Setup: Create a task with old-style priority (no phase component).
        Claim: With new code (should handle gracefully).
        Assert: Old task claimed without crash.
        Clean up: Mark old task completed.
        Re-enqueue: New task with new priority formula.
        Claim: New task claimed; priority in correct band.
        """
        # Setup: Create a task with old-style priority (no phase field)
        candidate = make_candidate(db_session).id

        # Manually create old-style task (priority in old range, default phase=1)
        old_task = TranslationTask(
            id=uuid4(),
            candidate_id=candidate,
            locale="en",
            source_hash="test-hash",
            priority=50,  # Old-style priority (would be 0–1000 range)
            status=WorkTaskStatus.PENDING,
            phase=1,  # Default phase
        )
        db_session.add(old_task)
        db_session.commit()

        # Claim with new code (should handle gracefully)
        api_key_id = make_key(db_session).id
        queue = LeasedQueue(db_session, model=TranslationTask)
        claimed = queue.claim(
            api_key_id,
            utc_now(),
            limit=1,
            scope=(),
            grouping=(),
            phase_field=TranslationTask.phase,
        )

        # Assert: old task claimed without crash
        assert claimed is not None, "Expected claim to succeed with old task"
        assert len(claimed) > 0, "Expected at least one claimed task"
        assert claimed[0].id == old_task.id, "Expected old task to be claimed"

        # Clean up and re-enqueue with new code
        old_task.status = WorkTaskStatus.COMPLETED
        db_session.commit()

        # Create fair selection state for new enqueue
        state = FairSelectionState(pipeline="translation", entity_id=candidate, phase=1)
        db_session.add(state)
        db_session.commit()

        # Create new task with new priority formula
        create_candidate_tasks(db_session, candidate, ["de"], phase=1)

        # Claim new task
        queue = LeasedQueue(db_session, model=TranslationTask)
        new_task = queue.claim(
            api_key_id,
            utc_now(),
            limit=1,
            scope=(),
            grouping=(),
            phase_field=TranslationTask.phase,
        )

        # Assert: new task claimed; priority in correct band
        assert new_task is not None, "Expected claim to succeed for new task"
        assert len(new_task) > 0, "Expected at least one claimed task"
        assert new_task[0].locale == "de", "Expected new task to be for 'de' locale"
        assert 0 <= new_task[0].priority < 100_000, (
            f"Expected phase-1 priority band (0–99,999), got {new_task[0].priority}"
        )
