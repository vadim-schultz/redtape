"""Snapshot phase priority (chapter C5): phase component in snapshot translation task priorities."""

from __future__ import annotations

import pytest
from app.features.translation.snapshot_enqueue import SnapshotEnqueuer
from app.models.discovery import CatalogueService, DiscoveryCandidateMention, DiscoveryMentionRole
from app.models.fair_selection_state import FairSelectionState
from app.models.snapshot_translation import SnapshotTranslationTask
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session

from search_support import make_candidate
from snapshot_machine_support import SHA_A, add_snapshot
from test_discovery_admin_api import _catalogue
from test_discovery_candidates_api import _item


def _scored_mention(session: Session, page: CatalogueService, confidence: float) -> None:
    """Persist a candidate on ``page`` whose one category carries ``confidence`` as its direct confidence."""
    candidate = make_candidate(session)
    session.add(
        DiscoveryCandidateMention(
            candidate_id=candidate.id,
            catalogue_service_id=page.id,
            role=DiscoveryMentionRole.REQUIRED,
            excerpt="Bitte bringen Sie Ihren Personalausweis mit.",
            source_field="details[0]",
            extractor="pvog_payload",
            extractor_version="1",
            category_codes=["home-and-housing"],
            direct_category_confidence=confidence,
        )
    )
    session.flush()


@pytest.fixture
def vocabulary(db_session: Session) -> None:
    seed_canonical_taxonomy(db_session)


def _page(session: Session, external_id: str) -> tuple[object, float]:
    """Create a page with a snapshot and a mention, returning (page_id, confidence)."""
    catalogue = _catalogue(session, external_id=external_id)
    add_snapshot(session, catalogue, SHA_A)
    return catalogue.id, 0.9  # Placeholder confidence


def test_get_phase_for_page_reads_from_state(db_session: Session) -> None:
    """Verify get_phase_for_page reads phase from fair_selection_state."""
    import uuid

    from app.features.translation.source import get_phase_for_page

    page_id = uuid.uuid4()

    # Create a FairSelectionState entry for this page with phase=2
    state = FairSelectionState(pipeline="translation", entity_id=page_id, phase=2)
    db_session.add(state)
    db_session.commit()

    phase = get_phase_for_page(db_session, page_id)
    assert phase == 2, f"Expected phase 2, got {phase}"


def test_get_phase_for_page_defaults_to_one_when_not_found(db_session: Session) -> None:
    """Verify get_phase_for_page defaults to phase 1 when no entry exists."""
    import uuid

    from app.features.translation.source import get_phase_for_page

    page_id = uuid.uuid4()

    # Don't create any FairSelectionState entry
    phase = get_phase_for_page(db_session, page_id)
    assert phase == 1, f"Expected phase 1 (default), got {phase}"


def test_snapshot_enqueue_applies_phase_to_priority(
    db_session: Session,
    vocabulary: None,
) -> None:
    """Verify snapshot enqueue reads phase and applies it to task priority."""

    from app.features.translation.source import get_phases_for_pages

    # Create a page
    catalogue = _catalogue(db_session, external_id="page-phase-2")
    page_id = catalogue.id
    add_snapshot(db_session, catalogue, SHA_A)

    # Set page to phase=2 in fair_selection_state
    state = FairSelectionState(pipeline="translation", entity_id=page_id, phase=2)
    db_session.add(state)
    db_session.commit()

    # Verify get_phases_for_pages returns phase 2
    phases = get_phases_for_pages(db_session, [page_id])
    assert phases[page_id] == 2, f"Expected phase 2 for page, got {phases[page_id]}"


def test_snapshot_enqueue_defaults_to_phase_one_when_not_in_state(
    db_session: Session,
    vocabulary: None,
) -> None:
    """Verify snapshot enqueue defaults to phase 1 when page has no state entry."""
    from app.features.translation.source import get_phases_for_pages

    # Create a page without a state entry
    catalogue = _catalogue(db_session, external_id="page-no-state")
    page_id = catalogue.id
    add_snapshot(db_session, catalogue, SHA_A)

    # Verify get_phases_for_pages returns phase 1 (default)
    phases = get_phases_for_pages(db_session, [page_id])
    assert phases[page_id] == 1, f"Expected phase 1 (default), got {phases[page_id]}"


def test_snapshot_phase_one_pages_rank_before_phase_two(db_session: Session, vocabulary: None) -> None:
    """Verify phase-1 snapshot tasks rank before phase-2 tasks."""
    # Create two pages with different phases
    page_a = _catalogue(db_session, external_id="page-a-phase1")
    page_b = _catalogue(db_session, external_id="page-b-phase2")

    add_snapshot(db_session, page_a, SHA_A)
    add_snapshot(db_session, page_b, SHA_A)

    # Create mentions for both pages
    _item(
        page_a,
        title_i18n={"de": "PageA"},
        source_field="details[0]",
        category_codes=["home-and-housing"],
        direct_category_confidence=0.3,  # Low confidence
    )
    _item(
        page_b,
        title_i18n={"de": "PageB"},
        source_field="details[0]",
        category_codes=["home-and-housing"],
        direct_category_confidence=0.9,  # High confidence
    )

    # Set page A to phase 1 (default), page B to phase 2
    state_b = FairSelectionState(pipeline="translation", entity_id=page_b.id, phase=2)
    db_session.add(state_b)
    db_session.commit()

    # Enqueue both pages
    enqueuer = SnapshotEnqueuer(db_session, ("en", "de"))
    enqueuer.enqueue_pages([page_a.id, page_b.id])

    # Query tasks sorted by priority
    tasks = list(db_session.query(SnapshotTranslationTask).order_by(SnapshotTranslationTask.priority.asc()).all())

    # Assert: 4 tasks (2 pages × 2 locales)
    assert len(tasks) == 4, f"Expected 4 tasks, got {len(tasks)}"

    # Assert: Page A's tasks (phase 1) come before page B's (phase 2)
    page_a_tasks = [t for t in tasks if t.catalogue_service_id == page_a.id]
    page_b_tasks = [t for t in tasks if t.catalogue_service_id == page_b.id]

    assert len(page_a_tasks) == 2, f"Expected 2 tasks for page A, got {len(page_a_tasks)}"
    assert len(page_b_tasks) == 2, f"Expected 2 tasks for page B, got {len(page_b_tasks)}"

    max_a_priority = max(t.priority for t in page_a_tasks)
    min_b_priority = min(t.priority for t in page_b_tasks)
    assert max_a_priority < min_b_priority, (
        f"All page A (phase 1) priorities should be < page B (phase 2). "
        f"Max A: {max_a_priority}, Min B: {min_b_priority}"
    )

    # Assert: Page A priorities in band 0–99,999; page B in 100,000–199,999
    for task in page_a_tasks:
        assert 0 <= task.priority < 100_000, f"Page A priority {task.priority} not in phase-1 band"
    for task in page_b_tasks:
        assert 100_000 <= task.priority < 200_000, f"Page B priority {task.priority} not in phase-2 band"


def test_snapshot_pages_of_same_phase_ordered_by_confidence_and_grouped_by_page(
    db_session: Session,
    vocabulary: None,
) -> None:
    """Verify within same phase, pages rank by confidence; locales of same page are grouped."""
    # Create two pages, both phase 1, different confidences
    page_high = _catalogue(db_session, external_id="page-high-conf")
    page_low = _catalogue(db_session, external_id="page-low-conf")

    add_snapshot(db_session, page_high, SHA_A)
    add_snapshot(db_session, page_low, SHA_A)

    # Create mentions with different confidences
    _scored_mention(db_session, page_high, 0.9)
    _scored_mention(db_session, page_low, 0.3)

    # Both default to phase 1
    db_session.commit()

    # Enqueue both pages
    enqueuer = SnapshotEnqueuer(db_session, ("en", "de"))
    enqueuer.enqueue_pages([page_high.id, page_low.id])

    # Query tasks sorted by priority
    tasks = list(db_session.query(SnapshotTranslationTask).order_by(SnapshotTranslationTask.priority.asc()).all())

    # Assert: 4 tasks (2 pages × 2 locales)
    assert len(tasks) == 4, f"Expected 4 tasks, got {len(tasks)}"

    # Assert: Page with high confidence comes first
    page_high_tasks = [t for t in tasks if t.catalogue_service_id == page_high.id]
    page_low_tasks = [t for t in tasks if t.catalogue_service_id == page_low.id]

    max_high_priority = max(t.priority for t in page_high_tasks)
    min_low_priority = min(t.priority for t in page_low_tasks)
    assert max_high_priority < min_low_priority, (
        f"High confidence page should rank before low confidence page within phase 1. "
        f"Max high: {max_high_priority}, Min low: {min_low_priority}"
    )

    # Assert: every locale of one page shares the page's priority, so the page's tasks stay together
    assert len({task.priority for task in page_high_tasks}) == 1, (
        f"Page high locales not grouped: {sorted(task.priority for task in page_high_tasks)}"
    )
