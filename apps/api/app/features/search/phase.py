"""Phase-aware priority and state tracking for embeddings (C6).

This module handles phase-state framework for the embedding pipeline:
- Phase component in priority calculation
- Reading phase for a candidate's embedding
- Coverage bitmap tracking
- Phase transition logic
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.fair_selection_state import FairSelectionState
from app.models.search import CandidateSearchText


def get_phase_for_embedding(session: Session, candidate_id: UUID) -> int:
    """Read phase for a candidate's embedding; default to phase 1 if not found.

    Args:
        session: Database session
        candidate_id: The candidate UUID

    Returns:
        The phase (default 1 if no state entry exists)
    """
    state = (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == "embedding",
            FairSelectionState.entity_id == candidate_id,
        )
        .first()
    )
    return state.phase if state else 1


def embedding_priority(phase: int = 1) -> int:
    """Calculate priority for an embedding task.

    Priority bands by phase:
      phase=1: 0–99,999 (breadth-first)
      phase=2: 100,000–199,999 (depth-first)
      phase=3: 200,000–299,999 (refresh)

    Within phase, all embeddings have the same priority (uniform distribution).

    Args:
        phase: The phase number (default 1)

    Returns:
        The priority value within the phase band
    """
    phase_band = (phase - 1) * 100_000
    return phase_band + 100  # constant offset; no confidence ranking


def get_embedding_coverage_for_candidate(session: Session, candidate_id: UUID) -> int:
    """Get the coverage bitmap for a candidate's embeddings.

    The coverage bitmap tracks which locales have completed embeddings
    via bit positions. Bit N is set if locale at index N is complete.

    Args:
        session: Database session
        candidate_id: The candidate UUID

    Returns:
        The coverage bitmap (0 if no state entry exists)
    """
    state = (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == "embedding",
            FairSelectionState.entity_id == candidate_id,
        )
        .first()
    )
    return state.coverage_bitmap if state else 0


def should_transition_embedding_phase_1_to_2(session: Session) -> bool:
    """Check if all candidates have embeddings in all locales (phase 1 → 2 trigger).

    This checks the phase 1 → 2 transition condition:
    All candidates must have coverage bitmap matching the full mask for the
    total number of locales in the system.

    Args:
        session: Database session

    Returns:
        True if phase 1 → 2 transition should occur, False otherwise
    """
    # Count total candidates with embeddings
    total_candidates = session.query(func.count(func.distinct(CandidateSearchText.candidate_id))).scalar() or 0

    if total_candidates == 0:
        return False

    # Count distinct locales
    num_locales = session.query(func.count(func.distinct(CandidateSearchText.locale))).scalar() or 0

    if num_locales == 0:
        return False

    # Full mask for all locales: (1 << num_locales) - 1
    full_mask = (1 << num_locales) - 1

    # Count candidates in phase 1 with full coverage
    complete_count = (
        session.query(func.count(func.distinct(FairSelectionState.entity_id)))
        .filter(
            FairSelectionState.pipeline == "embedding",
            FairSelectionState.phase == 1,
            FairSelectionState.coverage_bitmap == full_mask,
        )
        .scalar()
        or 0
    )

    # Phase 1 → 2 when ALL candidates have full coverage
    return complete_count >= total_candidates


def apply_embedding_phase_transition(session: Session) -> int:
    """Advance all phase-1 embeddings to phase 2 if conditions met.

    Args:
        session: Database session

    Returns:
        The number of state rows updated to phase 2
    """
    if not should_transition_embedding_phase_1_to_2(session):
        return 0

    return (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == "embedding",
            FairSelectionState.phase == 1,
        )
        .update({FairSelectionState.phase: 2}, synchronize_session=False)
    )
