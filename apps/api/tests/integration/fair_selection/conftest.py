"""Shared fixtures and helpers for fair task selection integration tests."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from app.features.search.leased_queue import LeasedQueue
from app.models.fair_selection_state import FairSelectionState
from app.models.search import EmbeddingTask, WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslationTask
from app.models.translation import TranslationTask
from sqlalchemy.orm import Session

from embedding_support import make_key
from search_support import make_candidate


@pytest.fixture
def session(db_session: Session) -> Generator[Session, None, None]:
    """Provide a database session for integration tests."""
    yield db_session


def create_candidate_tasks(
    session: Session,
    candidate_id: UUID | None = None,
    locales: list[str] | None = None,
    phase: int = 1,
    title: str = "Test Candidate",
) -> UUID:
    """Create a candidate with translation tasks across multiple locales.

    Args:
        session: SQLAlchemy session.
        candidate_id: If provided, use this candidate ID; otherwise create a new one.
        locales: List of locale codes (default: ["en"]).
        phase: Phase for task ordering (default 1).
        title: Candidate title for display.

    Returns:
        The candidate ID.
    """
    if locales is None:
        locales = ["en"]

    # Create candidate if not provided
    if candidate_id is None:
        candidate = make_candidate(session, title)
        candidate_id = candidate.id
        session.commit()

    # Create tasks for each locale
    for locale_index, locale in enumerate(locales):
        # The phase band, then the locale position so the locales of one candidate keep their order
        priority = (phase - 1) * 100_000 + locale_index
        task = TranslationTask(
            id=uuid4(),
            candidate_id=candidate_id,
            locale=locale,
            source_hash="test-hash",
            status=WorkTaskStatus.PENDING,
            priority=priority,
            phase=phase,
        )
        session.add(task)
    session.commit()

    return candidate_id


def setup_candidates_with_phase(
    session: Session,
    num_candidates: int,
    phase: int = 1,
    pipeline: str = "translation",
) -> list[UUID]:
    """Create N candidates with specified phase and coverage state.

    Args:
        session: SQLAlchemy session.
        num_candidates: Number of candidates to create.
        phase: Phase (1, 2, or 3).
        pipeline: Pipeline name.

    Returns:
        List of candidate UUIDs.
    """
    candidates = [uuid4() for _ in range(num_candidates)]
    for cid in candidates:
        state = FairSelectionState(pipeline=pipeline, entity_id=cid, phase=phase)
        session.add(state)
    session.commit()
    return candidates


def claim_all_tasks(
    session: Session,
    task_model: type[TranslationTask] | type[EmbeddingTask] | type[SnapshotTranslationTask],
    limit: int | None = None,
    grouping_field: str | None = None,
    phase_field: bool = True,
) -> list[TranslationTask | EmbeddingTask | SnapshotTranslationTask]:
    """Exhaust queue and return all claimed tasks in order.

    Args:
        session: SQLAlchemy session.
        task_model: Task model class (TranslationTask, EmbeddingTask, etc.)
        limit: Maximum total tasks to claim. If None, claim all available.
        grouping_field: Field name to group by (e.g., 'candidate_id').
        phase_field: Whether to use phase field in claim.

    Returns:
        List of all claimed tasks (up to limit if specified).
    """
    from app.features.search.clock import utc_now

    queue = LeasedQueue(session, model=task_model)
    claimed_tasks = []
    api_key_id = make_key(session).id
    now = utc_now()

    grouping = ()
    if grouping_field:
        grouping = (getattr(task_model, grouping_field),)

    phase_col = task_model.phase if phase_field else None
    scope = ()  # No additional filters for now

    # Determine batch size: either limit per call, or 100 at a time
    batch_size = limit or 100 if limit else 100

    while True:
        # Determine how many to claim in this batch
        if limit:
            remaining = limit - len(claimed_tasks)
            batch_size = min(batch_size, remaining)
            if batch_size <= 0:
                break

        tasks = queue.claim(
            api_key_id,
            now,
            limit=batch_size,
            scope=scope,
            grouping=grouping,
            phase_field=phase_col,
        )
        if not tasks:
            break
        claimed_tasks.extend(tasks)
        if limit and len(claimed_tasks) >= limit:
            break

    return claimed_tasks


def settle_tasks(
    session: Session,
    task_ids: list[UUID],
    task_model: type[TranslationTask] | type[EmbeddingTask] | type[SnapshotTranslationTask],
    status: WorkTaskStatus = WorkTaskStatus.COMPLETED,
) -> None:
    """Mark tasks as a specified status (default: COMPLETED).

    Args:
        session: SQLAlchemy session.
        task_ids: Task IDs to settle.
        task_model: Task model class.
        status: Status to set (default: COMPLETED).
    """
    for task_id in task_ids:
        task = session.query(task_model).filter(task_model.id == task_id).first()
        if task:
            task.status = status
    session.commit()
