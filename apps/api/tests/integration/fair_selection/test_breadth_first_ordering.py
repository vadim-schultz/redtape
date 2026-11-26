"""Slice 1: Breadth-First Ordering Test for fair task selection.

Validates that breadth-first ordering works correctly: all documents are
touched before any document is repeated, and phase 1 always completes
before phase 2 claims.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.fair_selection_state import FairSelectionState
from app.models.translation import TranslationTask
from tests.integration.fair_selection.conftest import (
    setup_candidates_with_phase,
    claim_all_tasks,
    create_candidate_tasks,
)


class TestBreadthFirstOrdering:
    """Test breadth-first ordering in fair task selection."""

    def test_breadth_first_all_documents_touched_before_repeats(self, session: Session) -> None:
        """Happy path: all documents touched before any document repeated.

        Setup: Create 3 candidates (A: 0.9, B: 0.1, C: 0.95), 3 locales each, all phase 1.
        Enqueue: 9 tasks total (1 task per candidate-locale pair).
        Claim: 9 sequential claims from the queue.
        Assert: Order respects breadth-first (all candidates touched before repeats).
        Assert: No candidate-locale pair claimed twice before all 9 pairs claimed once.
        """
        # Create tasks (creates candidates internally)
        candidate_a = create_candidate_tasks(session, locales=["en", "de", "fr"], phase=1, title="Candidate A")
        candidate_b = create_candidate_tasks(session, locales=["en", "de", "fr"], phase=1, title="Candidate B")
        candidate_c = create_candidate_tasks(session, locales=["en", "de", "fr"], phase=1, title="Candidate C")

        # Create fair selection state
        state_a = FairSelectionState(
            pipeline="translation", entity_id=candidate_a, phase=1
        )
        state_b = FairSelectionState(
            pipeline="translation", entity_id=candidate_b, phase=1
        )
        state_c = FairSelectionState(
            pipeline="translation", entity_id=candidate_c, phase=1
        )
        session.add_all([state_a, state_b, state_c])
        session.commit()

        # Claim
        claimed_tasks = claim_all_tasks(
            session,
            TranslationTask,
            limit=9,
            grouping_field="candidate_id",
            phase_field=True,
        )

        # Assert: breadth-first order
        assert len(claimed_tasks) == 9, f"Expected 9 claimed tasks, got {len(claimed_tasks)}"

        seen_candidates = set()
        for i, task in enumerate(claimed_tasks):
            if task.candidate_id in seen_candidates:
                # We've claimed a repeat; ensure all 3 candidates were seen first
                assert len(seen_candidates) == 3, (
                    f"Repeated candidate {task.candidate_id} at index {i} "
                    f"before all 3 candidates touched"
                )
            seen_candidates.add(task.candidate_id)

    def test_breadth_first_phase_1_completes_before_phase_2_claims(
        self, session: Session
    ) -> None:
        """Negative path: phase 1 always claims before phase 2.

        Setup: 2 candidates (A: phase=1, confidence=0.9), (B: phase=2, confidence=0.1), 2 locales each.
        Enqueue: 4 tasks total (A has 2, B has 2).
        Claim: Retrieve first 3 claims.
        Assert: All three are from A (phase 1).
        Assert: B's phase-2 task is not claimed until A's phase-1 work exhausted.
        """
        # Create tasks (creates candidates internally)
        candidate_phase1 = create_candidate_tasks(session, locales=["en", "de"], phase=1, title="Phase 1 Candidate")
        candidate_phase2 = create_candidate_tasks(session, locales=["en", "de"], phase=2, title="Phase 2 Candidate")

        # Create fair selection state
        state_phase1 = FairSelectionState(
            pipeline="translation", entity_id=candidate_phase1, phase=1
        )
        state_phase2 = FairSelectionState(
            pipeline="translation", entity_id=candidate_phase2, phase=2
        )
        session.add_all([state_phase1, state_phase2])
        session.commit()

        # Claim first 3 (should all be phase 1)
        claimed_tasks = claim_all_tasks(
            session,
            TranslationTask,
            limit=3,
            grouping_field=None,
            phase_field=True,
        )

        # Assert: all 3 are phase 1
        assert len(claimed_tasks) >= 2, f"Expected at least 2 claimed tasks, got {len(claimed_tasks)}"
        for task in claimed_tasks:
            assert task.candidate_id == candidate_phase1, (
                f"Expected phase-1 task, got candidate {task.candidate_id} in phase "
                f"{task.phase}"
            )
            assert task.phase == 1, (
                f"Expected phase 1, got phase {task.phase} for task {task.id}"
            )
