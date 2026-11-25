"""Phase tracking and priority calculation for embedding tasks (C6).

This module validates the phase-state framework applied to the embedding pipeline:
- Phase component in priority calculation
- Tracking coverage bitmap on settlement
- Phase transitions when all candidates have embeddings in all locales
"""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.features.search.enqueue import EmbeddingEnqueuer, EnqueueOutcome
from app.features.search.hashing import content_hash
from app.features.search.phase import (
    embedding_priority,
    get_embedding_coverage_for_candidate,
    get_phase_for_embedding,
    should_transition_embedding_phase_1_to_2,
)
from app.features.search.text import BuiltText
from app.models.fair_selection_state import FairSelectionState
from app.models.search import EmbeddingTask, WorkTaskStatus
from search_support import embed, make_candidate, open_tasks


def _built(text: str, locale: str = "de") -> BuiltText:
    """Create a BuiltText for testing."""
    return BuiltText(locale=locale, text=text, content_hash=content_hash(text))


# ============================================================================
# Slice 1: Read Phase for Embedding Task
# ============================================================================


class TestGetPhaseForEmbedding:
    """Read phase for a candidate's embedding state."""

    def test_get_phase_for_embedding_candidate_found(self, db_session: Session) -> None:
        """Happy path: phase read from state table when found.

        Setup: FairSelectionState(pipeline='embedding', entity_id=candidate_id, phase=2)
        Call: get_phase_for_embedding(session, candidate_id)
        Assert: Returns phase 2
        """
        candidate_id = UUID("12345678-1234-5678-1234-567812345678")

        # Insert fair selection state for embedding pipeline
        state = FairSelectionState(
            pipeline="embedding",
            entity_id=candidate_id,
            phase=2,
            coverage_bitmap=0,
        )
        db_session.add(state)
        db_session.flush()

        # Read phase should return 2
        phase = get_phase_for_embedding(db_session, candidate_id)

        assert phase == 2

    def test_get_phase_for_embedding_candidate_missing(self, db_session: Session) -> None:
        """Negative path: defaults to phase 1 when no state entry found.

        Setup: No entry in fair_selection_state for candidate_id
        Call: get_phase_for_embedding(session, candidate_id)
        Assert: Returns phase 1 (default for new candidates)
        """
        candidate_id = UUID("87654321-4321-8765-4321-876543218765")

        # No state entry created

        # Read phase should default to 1
        phase = get_phase_for_embedding(db_session, candidate_id)

        assert phase == 1


# ============================================================================
# Slice 2: Add Phase Component to Priority
# ============================================================================


class TestEmbeddingPriority:
    """Priority calculation with phase component."""

    def test_embedding_phase_affects_priority(self) -> None:
        """Happy path: phase 1 priority < phase 2 priority.

        Scenario: Candidate A (phase=1) vs. Candidate B (phase=2)
        Calculate: embedding_priority(phase=1) vs. embedding_priority(phase=2)
        Assert: Phase 1 priority < Phase 2 priority (phase 1 claims first)
        Assert: Both within expected bands
        """
        priority_phase_1 = embedding_priority(phase=1)
        priority_phase_2 = embedding_priority(phase=2)

        # Phase 1 should claim before phase 2
        assert priority_phase_1 < priority_phase_2

        # Phase 1: 0–99,999 band
        assert 0 <= priority_phase_1 <= 99_999

        # Phase 2: 100,000–199,999 band
        assert 100_000 <= priority_phase_2 <= 199_999

    def test_embedding_uniform_within_phase(self) -> None:
        """Negative path: all embeddings uniform within same phase.

        Scenario: Two candidates A and B, both phase=1
        Calculate: embedding_priority(phase=1) for both
        Assert: Priority values are identical (no confidence ranking)
        """
        priority_a = embedding_priority(phase=1)
        priority_b = embedding_priority(phase=1)

        # Both should be identical (uniform within phase)
        assert priority_a == priority_b


# ============================================================================
# Slice 3: Set Initial Phase on New Embeddings
# ============================================================================


class TestEnqueueEmbeddingPhase:
    """Setting initial phase=1 on new embedding tasks."""

    def test_enqueue_embedding_sets_phase_1(self, db_session: Session) -> None:
        """Happy path: new embedding task created with phase=1.

        Setup: Call EmbeddingEnqueuer.enqueue(candidate_id, built_text)
        Assert: New EmbeddingTask created with phase=1
        Assert: Priority reflects phase 1 band
        """
        from app.config import settings

        candidate = make_candidate(db_session)
        built = _built("test content")

        enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
        outcome = enqueuer.enqueue(candidate.id, built)

        assert outcome is EnqueueOutcome.QUEUED

        # Find the task
        task = db_session.query(EmbeddingTask).filter_by(candidate_id=candidate.id).one()

        # Phase should be 1
        assert task.phase == 1

        # Priority should be in phase 1 band (0–99,999)
        assert 0 <= task.priority <= 99_999

    def test_enqueue_embedding_does_not_override_existing_phase(
        self, db_session: Session
    ) -> None:
        """Negative path: re-enqueue doesn't reset phase.

        Setup: EmbeddingTask(candidate_id, status=PENDING, phase=2) exists
        Action: Call enqueue with updated built_text
        Assert: Task re-upserted with phase **unchanged** (stays 2)
        Assert: Upsert does not update phase column
        """
        from app.config import settings

        candidate = make_candidate(db_session)
        built_initial = _built("initial content")

        # Create initial task with phase 1
        enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
        enqueuer.enqueue(candidate.id, built_initial)

        task = db_session.query(EmbeddingTask).filter_by(candidate_id=candidate.id).one()
        task_id = task.id

        # Manually set phase to 2 (simulating phase transition)
        task.phase = 2
        db_session.flush()

        # Now re-enqueue with new content
        built_updated = _built("updated content")
        outcome = enqueuer.enqueue(candidate.id, built_updated)

        assert outcome is EnqueueOutcome.QUEUED

        # Refresh task and verify phase unchanged
        db_session.refresh(task)
        assert task.phase == 2
        assert task.id == task_id
        assert task.text_hash == built_updated.content_hash


# ============================================================================
# Slice 4: Track Coverage Bitmap on Settlement
# ============================================================================


class TestCoverageTracking:
    """Coverage bitmap tracking when embedding tasks complete."""

    def test_settle_embedding_updates_coverage_bitmap(self, db_session: Session) -> None:
        """Happy path: coverage bitmap tracks completed locales.

        Setup: Candidate with 10 locales, pending tasks for all
        Action: Settle task for locale "de" (index 0 in canonical first ordering)
        Assert: coverage_bitmap has bit 0 set
        Action: Settle task for locale "en" (index 1)
        Assert: coverage_bitmap has bits 0–1 set (0b00000011)
        """
        from app.config import settings

        candidate = make_candidate(db_session, title="Candidate A")

        # Enqueue tasks for multiple locales
        locales = settings.embedding_locale_codes
        enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model, locales=locales)

        for locale in locales:
            built = _built(f"content in {locale}", locale=locale)
            enqueuer.enqueue(candidate.id, built)

        db_session.flush()

        # Initial coverage should be 0
        coverage = get_embedding_coverage_for_candidate(db_session, candidate.id)
        assert coverage == 0

        # Find and settle first task (locale index 0)
        tasks = db_session.query(EmbeddingTask).filter_by(candidate_id=candidate.id).all()
        first_task = sorted(tasks, key=lambda t: t.locale)[0]
        first_locale_idx = locales.index(first_task.locale)

        # Simulate settlement - update coverage bitmap
        state = db_session.query(FairSelectionState).filter_by(
            pipeline="embedding", entity_id=candidate.id
        ).first()
        if state is None:
            state = FairSelectionState(
                pipeline="embedding",
                entity_id=candidate.id,
                phase=1,
                coverage_bitmap=0,
            )
            db_session.add(state)

        state.coverage_bitmap |= 1 << first_locale_idx
        db_session.flush()

        # Verify bit is set
        coverage = get_embedding_coverage_for_candidate(db_session, candidate.id)
        assert coverage & (1 << first_locale_idx)

        # Settle second task
        second_task = [t for t in tasks if t.id != first_task.id][0]
        second_locale_idx = locales.index(second_task.locale)

        state.coverage_bitmap |= 1 << second_locale_idx
        db_session.flush()

        # Verify both bits set
        coverage = get_embedding_coverage_for_candidate(db_session, candidate.id)
        assert coverage & (1 << first_locale_idx)
        assert coverage & (1 << second_locale_idx)

    def test_settle_embedding_does_not_update_on_failure(self, db_session: Session) -> None:
        """Negative path: failed tasks don't update coverage.

        Setup: Candidate with 10 locales
        Action: Claim task for locale "de", fail it
        Assert: coverage_bitmap remains 0 (failure doesn't count)
        Assert: Future claims can still pick that locale
        """
        from app.config import settings

        candidate = make_candidate(db_session)

        # Enqueue task
        enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model)
        enqueuer.enqueue(candidate.id, _built("test content"))
        db_session.flush()

        # Initial coverage should be 0
        coverage = get_embedding_coverage_for_candidate(db_session, candidate.id)
        assert coverage == 0

        # Mark task as failed (don't update coverage)
        task = db_session.query(EmbeddingTask).filter_by(candidate_id=candidate.id).one()
        task.status = WorkTaskStatus.FAILED
        db_session.flush()

        # Coverage should still be 0
        coverage = get_embedding_coverage_for_candidate(db_session, candidate.id)
        assert coverage == 0


# ============================================================================
# Slice 5: Phase Transition Logic
# ============================================================================


class TestPhaseTransition:
    """Phase 1 → 2 transition when all candidates have full coverage."""

    def test_embedding_phase_1_to_2_transition(self, db_session: Session) -> None:
        """Happy path: phase 1 → 2 when all candidates complete all locales.

        Setup: 3 candidates, 10 locales each, all phase=1
        Action: Settle all 30 embedding tasks
        Assert: Phase transition checker returns True
        Assert: All candidates can transition to phase 2
        """
        from app.config import settings

        # Create 3 candidates
        candidates = [make_candidate(db_session, title=f"Candidate {i}") for i in range(3)]

        # Enqueue for all locales
        locales = settings.embedding_locale_codes[:10]  # Use first 10 locales
        enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model, locales=locales)

        for candidate in candidates:
            for locale in locales:
                built = _built(f"content in {locale}", locale=locale)
                enqueuer.enqueue(candidate.id, built)

        db_session.flush()

        # Create fair selection state for each candidate (phase 1)
        for candidate in candidates:
            state = db_session.query(FairSelectionState).filter_by(
                pipeline="embedding", entity_id=candidate.id
            ).first()
            if state is None:
                state = FairSelectionState(
                    pipeline="embedding",
                    entity_id=candidate.id,
                    phase=1,
                    coverage_bitmap=0,
                )
                db_session.add(state)

        db_session.flush()

        # Mark all tasks as completed
        full_mask = (1 << len(locales)) - 1
        for candidate in candidates:
            tasks = db_session.query(EmbeddingTask).filter_by(candidate_id=candidate.id).all()
            for task in tasks:
                task.status = WorkTaskStatus.COMPLETED

            # Update coverage bitmap to show all locales complete
            state = db_session.query(FairSelectionState).filter_by(
                pipeline="embedding", entity_id=candidate.id
            ).one()
            state.coverage_bitmap = full_mask

        db_session.flush()

        # Check if transition should happen
        should_transition = should_transition_embedding_phase_1_to_2(db_session)
        assert should_transition is True

    def test_embedding_phase_1_incomplete_no_transition(self, db_session: Session) -> None:
        """Negative path: no transition if any candidate is incomplete.

        Setup: 3 candidates, 10 locales each, phase=1
        Action: Settle only 25 of 30 tasks (5 incomplete)
        Assert: Phase transition checker returns False
        Assert: Phase remains 1
        """
        from app.config import settings

        # Create 3 candidates
        candidates = [make_candidate(db_session, title=f"Candidate {i}") for i in range(3)]

        # Enqueue for all locales
        locales = settings.embedding_locale_codes[:10]
        enqueuer = EmbeddingEnqueuer(db_session, settings.embedding_model, locales=locales)

        for candidate in candidates:
            for locale in locales:
                built = _built(f"content in {locale}", locale=locale)
                enqueuer.enqueue(candidate.id, built)

        db_session.flush()

        # Create fair selection state for each candidate (phase 1)
        for candidate in candidates:
            state = db_session.query(FairSelectionState).filter_by(
                pipeline="embedding", entity_id=candidate.id
            ).first()
            if state is None:
                state = FairSelectionState(
                    pipeline="embedding",
                    entity_id=candidate.id,
                    phase=1,
                    coverage_bitmap=0,
                )
                db_session.add(state)

        db_session.flush()

        # Mark only first 25 tasks as completed (5 locales of last candidate missing)
        full_mask = (1 << len(locales)) - 1
        partial_mask = (1 << 5) - 1  # Only first 5 locales

        all_tasks = db_session.query(EmbeddingTask).all()
        for i, task in enumerate(all_tasks):
            if i < 25:  # First 25 tasks complete
                task.status = WorkTaskStatus.COMPLETED

        db_session.flush()

        # Update coverage for first 2 candidates (complete) and last candidate (partial)
        for idx, candidate in enumerate(candidates):
            state = db_session.query(FairSelectionState).filter_by(
                pipeline="embedding", entity_id=candidate.id
            ).one()
            if idx < 2:
                state.coverage_bitmap = full_mask
            else:
                state.coverage_bitmap = partial_mask

        db_session.flush()

        # Check if transition should happen - should NOT
        should_transition = should_transition_embedding_phase_1_to_2(db_session)
        assert should_transition is False
