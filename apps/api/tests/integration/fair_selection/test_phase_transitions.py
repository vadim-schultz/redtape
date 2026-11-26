"""Slice 2: Phase Transition Trigger Test for fair task selection.

Validates that phase transitions happen automatically when coverage is complete,
and doesn't trigger prematurely while a document is still uncovered.
"""

from __future__ import annotations

from app.features.fair_selection.state_machine import (
    check_phase_one_complete,
    transition_phase,
)
from app.models.fair_selection_state import FairSelectionState
from app.models.search import WorkTaskStatus
from app.models.translation import TranslationTask
from sqlalchemy.orm import Session
from tests.integration.fair_selection.conftest import (
    create_candidate_tasks,
)

from fair_selection_support import candidate_ids


class TestPhaseTransitions:
    """Test phase transition logic in fair task selection."""

    def test_phase_transition_1_to_2_on_coverage_complete(self, session: Session) -> None:
        """Happy path: phase 1 → 2 transition triggers when all documents covered.

        Setup: 2 candidates (each phase 1), 2 locales each = 4 tasks.
        Enqueue: All 4 tasks.
        Settle: Mark all 4 tasks as COMPLETED.
        Assert: Before settle, both candidates still phase 1.
        Assert: After settle, check passes and candidates can transition to phase 2.
        """
        candidate_a, candidate_b = candidate_ids(session, 2)

        state_a = FairSelectionState(pipeline="translation", entity_id=candidate_a, phase=1)
        state_b = FairSelectionState(pipeline="translation", entity_id=candidate_b, phase=1)
        session.add_all([state_a, state_b])
        session.commit()

        # Create tasks
        create_candidate_tasks(session, candidate_a, ["en", "de"], phase=1)
        create_candidate_tasks(session, candidate_b, ["en", "de"], phase=1)

        # Settle all tasks
        tasks = session.query(TranslationTask).all()
        for task in tasks:
            task.status = WorkTaskStatus.COMPLETED
        session.commit()

        # Check phase 1 complete before transition
        is_complete = check_phase_one_complete("translation", session=session)
        assert is_complete, "Expected check_phase_one_complete to return True after settling all tasks"

        # Trigger state transition
        updated = transition_phase("translation", 1, 2, session=session)
        session.commit()

        assert updated == 2, f"Expected both phase-1 states to transition, got {updated}"
        # Assert: Both candidates transitioned to phase 2
        session.refresh(state_a)
        session.refresh(state_b)
        assert state_a.phase == 2, f"Expected phase 2 for state_a, got {state_a.phase}"
        assert state_b.phase == 2, f"Expected phase 2 for state_b, got {state_b.phase}"

    def test_phase_transition_1_to_2_does_not_trigger_until_all_complete(self, session: Session) -> None:
        """Negative path: phase 1 → 2 doesn't trigger while one document is still uncovered.

        Setup: 2 candidates (each phase 1), 2 locales each = 4 tasks.
        Settle: Both tasks of candidate A; none of candidate B.
        Assert: check_phase_one_complete returns False.
        Assert: Transition updates nothing and both candidates remain phase 1.
        """
        candidate_a, candidate_b = candidate_ids(session, 2)

        state_a = FairSelectionState(pipeline="translation", entity_id=candidate_a, phase=1)
        state_b = FairSelectionState(pipeline="translation", entity_id=candidate_b, phase=1)
        session.add_all([state_a, state_b])
        session.commit()

        # Create tasks
        create_candidate_tasks(session, candidate_a, ["en", "de"], phase=1)
        create_candidate_tasks(session, candidate_b, ["en", "de"], phase=1)

        # Settle candidate A's tasks only, so candidate B stays uncovered
        for task in session.query(TranslationTask).filter(TranslationTask.candidate_id == candidate_a).all():
            task.status = WorkTaskStatus.COMPLETED
        session.commit()

        # Check phase 1 complete
        is_complete = check_phase_one_complete("translation", session=session)
        assert not is_complete, "Expected check_phase_one_complete to return False while candidate B is uncovered"

        # Try to trigger state transition (should not update anything)
        updated = transition_phase("translation", 1, 2, session=session)
        session.commit()

        assert updated == 0, f"Expected a blocked transition to update nothing, got {updated}"
        # Assert: Both candidates still phase 1
        session.refresh(state_a)
        session.refresh(state_b)
        assert state_a.phase == 1, f"Expected phase 1 with partial completion, got {state_a.phase}"
        assert state_b.phase == 1, f"Expected phase 1 with partial completion, got {state_b.phase}"
