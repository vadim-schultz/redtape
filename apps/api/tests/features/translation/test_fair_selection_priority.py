"""Tests for translation priority calculation with phase support.

This module validates that the priority formula includes a phase component,
ensuring phase-1 tasks always rank above phase-2 tasks, while maintaining
backward compatibility with existing confidence-based ordering.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.features.translation.priority import (
    first_priority,
    retranslation_priority,
)
from app.features.translation.source import (
    get_phase_for_candidate,
    get_phases_for_candidates,
)
from app.models.fair_selection_state import FairSelectionState


# ============================================================================
# Slice 1: Read Phase from Database
# ============================================================================


class TestGetPhaseForCandidate:
    """Validate reading phase from fair_selection_state."""

    def test_read_phase_for_candidate_happy_path(self, db_session: Session) -> None:
        """Happy path: read phase for a candidate from fair_selection_state.

        Setup: FairSelectionState(pipeline='translation', entity_id=candidate_id, phase=2)
        Call: get_phase_for_candidate(db_session, candidate_id) -> returns 2
        Assert: Correct phase read
        """
        candidate_id = uuid4()

        # Create state entry with phase 2
        state = FairSelectionState(
            pipeline="translation",
            entity_id=candidate_id,
            phase=2,
            coverage_bitmap=0,
        )
        db_session.add(state)
        db_session.flush()

        # Read phase
        phase = get_phase_for_candidate(db_session, candidate_id)

        # Verify
        assert phase == 2, f"Expected phase 2, got {phase}"

    def test_read_phase_for_candidate_negative_path(self, db_session: Session) -> None:
        """Negative path: missing phase entry returns default phase 1.

        Setup: No entry in fair_selection_state for candidate_id
        Call: get_phase_for_candidate(db_session, candidate_id) -> returns 1
        Assert: Doesn't crash; assumes phase 1
        """
        candidate_id = uuid4()

        # No state entry created
        phase = get_phase_for_candidate(db_session, candidate_id)

        # Verify default phase 1
        assert phase == 1, f"Expected default phase 1, got {phase}"


class TestGetPhasesForCandidates:
    """Validate batch reading of phases."""

    def test_read_phases_for_candidates_happy_path(self, db_session: Session) -> None:
        """Happy path: read phases for multiple candidates.

        Setup: Create states for 3 candidates with phases 1, 2, 2
        Call: get_phases_for_candidates(db_session, [cid1, cid2, cid3])
        Assert: Returns dict with correct phases
        """
        candidate_ids = [uuid4(), uuid4(), uuid4()]
        phases_input = [1, 2, 2]

        # Create state entries
        for cid, phase in zip(candidate_ids, phases_input):
            state = FairSelectionState(
                pipeline="translation",
                entity_id=cid,
                phase=phase,
                coverage_bitmap=0,
            )
            db_session.add(state)
        db_session.flush()

        # Read phases
        phases = get_phases_for_candidates(db_session, candidate_ids)

        # Verify
        assert phases == {
            candidate_ids[0]: 1,
            candidate_ids[1]: 2,
            candidate_ids[2]: 2,
        }

    def test_read_phases_for_candidates_negative_path(self, db_session: Session) -> None:
        """Negative path: missing entries default to phase 1.

        Setup: Create state for 1 candidate, query 3 candidates
        Call: get_phases_for_candidates(db_session, [cid1, cid2, cid3])
        Assert: cid1 is 2, cid2 and cid3 default to 1
        """
        candidate_ids = [uuid4(), uuid4(), uuid4()]

        # Create state only for first candidate
        state = FairSelectionState(
            pipeline="translation",
            entity_id=candidate_ids[0],
            phase=2,
            coverage_bitmap=0,
        )
        db_session.add(state)
        db_session.flush()

        # Read phases
        phases = get_phases_for_candidates(db_session, candidate_ids)

        # Verify
        assert phases == {
            candidate_ids[0]: 2,
            candidate_ids[1]: 1,
            candidate_ids[2]: 1,
        }


# ============================================================================
# Slice 2: Modify Priority Formula to Include Phase
# ============================================================================


class TestPriorityFormulaWithPhase:
    """Validate that phase component is applied correctly."""

    def test_phase_component_applied_happy_path(self) -> None:
        """Happy path: phase component applied correctly.

        Scenario: Candidate A (confidence=0.9, phase=1) vs.
                  Candidate B (confidence=0.9, phase=2)
        Calculate: first_priority(0.9, phase=1) vs. first_priority(0.9, phase=2)
        Assert: A's priority < B's (phase 1 ranks before phase 2)
                A in band 0–99,999; B in band 100,000–199,999
        """
        p1 = first_priority(0.9, phase=1)
        p2 = first_priority(0.9, phase=2)

        # Phase 1 should be in band 0–99,999
        assert 0 <= p1 < 100_000, f"Phase 1 priority {p1} not in band 0–99,999"

        # Phase 2 should be in band 100,000–199,999
        assert 100_000 <= p2 < 200_000, f"Phase 2 priority {p2} not in band 100,000–199,999"

        # Phase 1 should rank before phase 2
        assert p1 < p2, f"Phase 1 {p1} should < Phase 2 {p2}"

    def test_confidence_ordering_within_phase_negative_path(self) -> None:
        """Negative path: within same phase, confidence order preserved.

        Scenario: Candidate A (confidence=0.9, phase=1) vs.
                  Candidate B (confidence=0.3, phase=1)
        Calculate: first_priority(0.9, phase=1) vs. first_priority(0.3, phase=1)
        Assert: A's priority < B's (high confidence comes first, as before)
        """
        p_high = first_priority(0.9, phase=1)
        p_low = first_priority(0.3, phase=1)

        # High confidence should rank before low confidence
        assert p_high < p_low, f"High confidence {p_high} should < low confidence {p_low}"

        # Both should be in same phase band
        assert 0 <= p_high < 100_000
        assert 0 <= p_low < 100_000


class TestRetranslationPriorityWithPhase:
    """Validate retranslation priority includes phase component."""

    def test_retranslation_priority_respects_phase(self) -> None:
        """Verify retranslation priority includes phase component.

        Scenario: Retranslation task at confidence 0.9
        Calculate: retranslation_priority(0.9, phase=1) vs.
                   retranslation_priority(0.9, phase=2)
        Assert: Phase 1 ranks before phase 2
                Within phase bands (10,000–110,000 for phase 1, etc.)
        """
        rp1 = retranslation_priority(0.9, phase=1)
        rp2 = retranslation_priority(0.9, phase=2)

        # Phase 1 retranslation in band 10,000–109,999
        assert 10_000 <= rp1 < 110_000

        # Phase 2 retranslation in band 110,000–209,999
        assert 110_000 <= rp2 < 210_000

        # Phase 1 ranks before phase 2
        assert rp1 < rp2


# ============================================================================
# Slice 4: Locale Index for Grouping (future test placeholder)
# ============================================================================


class TestLocaleIndexTiebreak:
    """Validate locale_index provides stable tie-breaking."""

    def test_locale_index_provides_stable_tiebreak(self) -> None:
        """Verify locale_index ensures adjacent priorities.

        Scenario: Same candidate (confidence=0.9, phase=1), different locales
        Calculate: priority with locale_index 0, 1, 2, ...
        Assert: Priorities differ by 1 for each locale index
        """
        p0 = first_priority(0.9, phase=1, locale_index=0)
        p1 = first_priority(0.9, phase=1, locale_index=1)
        p2 = first_priority(0.9, phase=1, locale_index=2)

        # Locale indices should produce adjacent priorities
        assert p1 == p0 + 1, f"Locale indices should differ by 1: {p1} vs {p0}"
        assert p2 == p1 + 1, f"Locale indices should differ by 1: {p2} vs {p1}"
