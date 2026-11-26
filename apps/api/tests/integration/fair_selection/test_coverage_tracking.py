"""Slice 3: Coverage Tracking Bitmap Audit Test for fair task selection.

Validates that coverage bitmaps are updated correctly when tasks complete,
and that the system correctly identifies when coverage is complete for a document.
"""

from __future__ import annotations

from uuid import uuid4

from app.features.fair_selection.audit import audit_fair_selection_state
from app.features.translation.enqueue import TranslationEnqueuer
from app.models.fair_selection_state import FairSelectionState
from app.models.search import WorkTaskStatus
from app.models.translation import TranslationTask
from sqlalchemy.orm import Session
from tests.integration.fair_selection.conftest import create_candidate_tasks


class TestCoverageTracking:
    """Test coverage tracking and bitmap audit for fair task selection."""

    def test_coverage_bitmap_tracks_completed_tasks_correctly(self, session: Session) -> None:
        """Happy path: bitmap tracks completed tasks correctly.

        Setup: 1 candidate, 4 locales (en, de, fr, it), phase 1.
        Enqueue: 4 tasks.
        Settle: Mark tasks 0 (en) and 2 (fr) as COMPLETED.
        Assert: Bitmap = 0b0101 (bits 0 and 2 set).
        Query: "Is coverage complete?" → false (only 2 of 4 locales).
        Settle: Mark tasks 1 (de) and 3 (it) as COMPLETED.
        Assert: Bitmap = 0b1111 (all 4 bits set).
        Query: "Is coverage complete?" → true.
        """
        # Setup
        candidate = uuid4()
        state = FairSelectionState(pipeline="translation", entity_id=candidate, phase=1)
        session.add(state)
        session.commit()

        # Create tasks
        create_candidate_tasks(session, candidate, ["en", "de", "fr", "it"], phase=1)

        tasks = session.query(TranslationTask).filter(TranslationTask.candidate_id == candidate).all()
        assert len(tasks) == 4

        # Settle tasks 0 and 2 (en, fr)
        for task in [tasks[0], tasks[2]]:
            task.status = WorkTaskStatus.COMPLETED
        session.commit()

        # Audit
        report = audit_fair_selection_state(session, "translation", candidate)
        session.refresh(state)

        expected_bitmap = 0b0101  # bits 0 and 2 set
        assert state.coverage_bitmap == expected_bitmap, (
            f"Expected bitmap {bin(expected_bitmap)}, got {bin(state.coverage_bitmap)}"
        )

        # Check coverage complete query
        assert not report.is_complete, "Expected is_complete=False with 2 of 4 locales complete"

        # Settle remaining tasks
        for task in [tasks[1], tasks[3]]:
            task.status = WorkTaskStatus.COMPLETED
        session.commit()

        # Audit again
        report = audit_fair_selection_state(session, "translation", candidate)
        session.refresh(state)

        expected_bitmap = 0b1111  # all 4 bits set
        assert state.coverage_bitmap == expected_bitmap, (
            f"Expected bitmap {bin(expected_bitmap)}, got {bin(state.coverage_bitmap)}"
        )

        # Assert: coverage complete
        assert report.is_complete, "Expected is_complete=True with all 4 locales complete"

    def test_coverage_bitmap_ignores_claimed_not_completed(self, session: Session) -> None:
        """Negative path: bitmap only counts COMPLETED tasks, not CLAIMED.

        Setup: 1 candidate, 2 locales, phase 1.
        Enqueue: 2 tasks.
        Mark: Both tasks as CLAIMED (simulate worker claiming).
        Assert: Bitmap still = 0b00 (no completed tasks).
        Query: "Is coverage complete?" → false.
        Settle: Complete task 0.
        Assert: Bitmap = 0b01 (task 0 complete, task 1 still claimed).
        Query: "Is coverage complete?" → false (not all locales complete).
        """
        # Setup
        candidate = uuid4()
        state = FairSelectionState(pipeline="translation", entity_id=candidate, phase=1)
        session.add(state)
        session.commit()

        # Enqueue
        enqueuer = TranslationEnqueuer(session)
        enqueuer.enqueue_many([candidate], ["en", "de"])
        session.commit()

        # Claim (simulate worker claiming tasks)
        tasks = session.query(TranslationTask).filter(TranslationTask.candidate_id == candidate).all()
        for task in tasks:
            task.status = WorkTaskStatus.CLAIMED

        session.commit()

        # Audit
        report = audit_fair_selection_state(session, "translation", candidate)
        session.refresh(state)

        # Bitmap should still be 0 (no tasks completed)
        assert state.coverage_bitmap == 0, f"Expected bitmap 0 for claimed-only tasks, got {bin(state.coverage_bitmap)}"

        # Assert: coverage not complete
        assert not report.is_complete, "Expected is_complete=False with no completed tasks"

        # Complete task 0
        tasks[0].status = WorkTaskStatus.COMPLETED
        session.commit()

        # Audit again
        report = audit_fair_selection_state(session, "translation", candidate)
        session.refresh(state)

        expected_bitmap = 0b01  # bit 0 set
        assert state.coverage_bitmap == expected_bitmap, (
            f"Expected bitmap {bin(expected_bitmap)}, got {bin(state.coverage_bitmap)}"
        )

        # Still not complete (only 1 of 2 locales)
        assert not report.is_complete, "Expected is_complete=False with only 1 of 2 locales complete"
