"""Slice 3: Coverage Tracking Bitmap Audit Test for fair task selection.

Validates that the coverage bitmap is written by the audit from the tasks that have actually completed.
"""

from __future__ import annotations

import pytest
from app.features.fair_selection.audit import audit_fair_selection_state
from app.features.fair_selection.state_machine import check_phase_one_complete
from app.models.fair_selection_state import FairSelectionState
from app.models.search import WorkTaskStatus
from sqlalchemy.orm import Session

from fair_selection_support import translation_task
from search_support import make_candidate


def _track(session: Session, candidate_id: object) -> FairSelectionState:
    """Add the phase-1 translation state row of ``candidate_id`` and return it."""
    state = FairSelectionState(pipeline="translation", entity_id=candidate_id, phase=1)
    session.add(state)
    session.commit()
    return state


class TestCoverageTracking:
    """Test coverage tracking and bitmap audit for fair task selection."""

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Per-locale coverage bitmap is not implemented: the audit sets bit 0 once any task completed. "
            "The design docs disagree on what the bitmap means (00-architecture: task types; C6: locale index)."
        ),
    )
    def test_coverage_bitmap_tracks_each_completed_locale(self, session: Session) -> None:
        """Happy path: each completed locale sets its own bit, and the phase check passes once all four are done.

        Setup: 1 candidate, 4 locales (en, de, fr, it), phase 1.
        Settle: complete en and fr, audit: bitmap 0b0101.
        Settle: complete de and it, audit: bitmap 0b1111 and phase 1 complete.
        """
        candidate = make_candidate(session)
        state = _track(session, candidate.id)
        tasks = {locale: translation_task(session, candidate, locale=locale) for locale in ("en", "de", "fr", "it")}
        session.commit()

        for locale in ("en", "fr"):
            tasks[locale].status = WorkTaskStatus.COMPLETED
        session.commit()
        audit_fair_selection_state("translation", session=session)
        session.refresh(state)
        assert state.coverage_bitmap == 0b0101

        for locale in ("de", "it"):
            tasks[locale].status = WorkTaskStatus.COMPLETED
        session.commit()
        audit_fair_selection_state("translation", session=session)
        session.refresh(state)
        assert state.coverage_bitmap == 0b1111
        assert check_phase_one_complete("translation", session=session) is True

    def test_coverage_bitmap_ignores_claimed_not_completed(self, session: Session) -> None:
        """Negative path: claimed tasks do not set the bitmap; only a completed task does.

        Setup: 1 candidate, 2 locales (en, de), phase 1; both tasks claimed by a worker.
        Audit: bitmap stays 0.
        Settle: complete en, audit: bitmap is set (the audit's bit 0 is "any task completed").
        """
        candidate = make_candidate(session)
        state = _track(session, candidate.id)
        tasks = [
            translation_task(session, candidate, locale=locale, status=WorkTaskStatus.CLAIMED)
            for locale in ("en", "de")
        ]
        session.commit()

        audit_fair_selection_state("translation", session=session)
        session.refresh(state)
        assert state.coverage_bitmap == 0, f"Expected bitmap 0 for claimed-only tasks, got {bin(state.coverage_bitmap)}"

        tasks[0].status = WorkTaskStatus.COMPLETED
        session.commit()
        audit_fair_selection_state("translation", session=session)
        session.refresh(state)
        assert state.coverage_bitmap == 1, (
            f"Expected bit 0 set after a completed task, got {bin(state.coverage_bitmap)}"
        )
