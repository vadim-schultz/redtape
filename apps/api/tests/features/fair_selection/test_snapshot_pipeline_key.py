"""The snapshot pipeline answers to ``snapshot_translation``, the name its fair_selection_state rows carry."""

from __future__ import annotations

import pytest
from app.features.fair_selection.audit import audit_fair_selection_state
from app.features.fair_selection.state_machine import check_phase_one_complete
from app.models.fair_selection_state import FairSelectionState
from app.models.search import WorkTaskStatus
from sqlalchemy.orm import Session

from fair_selection_support import catalogue_page, snapshot_task


def _track_pages(session: Session, *pages_ids: object, phase: int = 1, coverage_bitmap: int = 0) -> None:
    """Add a snapshot-pipeline state row for each page id."""
    session.add_all(
        FairSelectionState(
            pipeline="snapshot_translation", entity_id=page_id, phase=phase, coverage_bitmap=coverage_bitmap
        )
        for page_id in pages_ids
    )
    session.commit()


class TestSnapshotPipelineName:
    """Phase check and audit read the snapshot pipeline under its stored name."""

    def test_phase_one_check_is_true_once_every_snapshot_page_has_a_completed_task(self, db_session: Session) -> None:
        """Happy path: the one tracked page has a completed snapshot task, so phase 1 is done."""
        page = catalogue_page(db_session)
        snapshot_task(db_session, page, status=WorkTaskStatus.COMPLETED)
        _track_pages(db_session, page.id)

        assert check_phase_one_complete("snapshot_translation", session=db_session) is True

    def test_phase_one_check_is_false_while_a_snapshot_page_has_no_completed_task(self, db_session: Session) -> None:
        """Negative path: one of two tracked pages is uncovered, so phase 1 stays open."""
        covered = catalogue_page(db_session)
        uncovered = catalogue_page(db_session)
        snapshot_task(db_session, covered, status=WorkTaskStatus.COMPLETED)
        _track_pages(db_session, covered.id, uncovered.id)

        assert check_phase_one_complete("snapshot_translation", session=db_session) is False

    def test_audit_sets_the_coverage_bitmap_from_the_snapshot_completions(self, db_session: Session) -> None:
        """Happy path: a stale bitmap of 0 is corrected to 1 because the page has a completed snapshot task."""
        page = catalogue_page(db_session)
        snapshot_task(db_session, page, status=WorkTaskStatus.COMPLETED)
        _track_pages(db_session, page.id)

        report = audit_fair_selection_state("snapshot_translation", session=db_session)

        assert (report.entities_checked, report.corrected) == (1, 1)
        (state,) = db_session.query(FairSelectionState).filter_by(pipeline="snapshot_translation").all()
        assert state.coverage_bitmap == 1


class TestUnknownPipelineNames:
    """Names no pipeline answers to are refused, and the retired key is one of them."""

    def test_an_unknown_pipeline_is_refused(self, db_session: Session) -> None:
        """Negative path: a name that maps to no pipeline raises ``ValueError``."""
        with pytest.raises(ValueError, match="Unknown pipeline: no_such_pipeline"):
            check_phase_one_complete("no_such_pipeline", session=db_session)

    def test_the_retired_translation_snapshot_key_is_refused(self, db_session: Session) -> None:
        """Negative path: the misspelt key ``translation_snapshot`` no longer names a pipeline."""
        with pytest.raises(ValueError, match="Unknown pipeline: translation_snapshot"):
            check_phase_one_complete("translation_snapshot", session=db_session)
