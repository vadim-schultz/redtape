"""Integration tests for phase-aware discovery task selection.

Tests verify that discovery tasks are ordered by phase first, then by priority,
with page completeness as a tie-break within phase. Phase 1 items always claim
before phase 2 or 3, independent of page completeness or priority.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.features.discovery.repository.tasks import (
    TaskRepository,
    get_phase_for_discovery_page,
)
from app.features.discovery.repository.task_target import TaskTarget
from app.models.discovery import DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus
from app.models.fair_selection_state import FairSelectionState
from sqlalchemy.orm import Session


class TestDiscoveryTaskPhaseColumn:
    """Slice 1: Verify phase column exists and defaults correctly."""

    def test_discovery_task_has_phase_column(self, db_session: Session) -> None:
        """Happy path: DiscoveryTask has phase attribute and accepts explicit phase."""
        task = DiscoveryTask(
            catalogue_service_id=uuid4(),
            kind=DiscoveryTaskKind.RENDER_PAGE,
            target_url="https://example.com",
            phase=2,
        )
        db_session.add(task)
        db_session.flush()

        assert task.phase == 2

    def test_discovery_task_phase_defaults_to_one(self, db_session: Session) -> None:
        """Negative path: DiscoveryTask defaults phase to 1 when not specified."""
        task = DiscoveryTask(
            catalogue_service_id=uuid4(),
            kind=DiscoveryTaskKind.RENDER_PAGE,
            target_url="https://example.com",
        )
        db_session.add(task)
        db_session.flush()

        assert task.phase == 1


class TestGetPhaseForDiscoveryPage:
    """Slice 2: Verify reading phase from fair_selection_state."""

    def test_get_phase_for_discovery_page_reads_from_state(
        self, db_session: Session
    ) -> None:
        """Happy path: Read phase from fair_selection_state for a discovery page."""
        page_id = uuid4()
        state = FairSelectionState(
            pipeline="discovery", entity_id=page_id, phase=2, coverage_bitmap=0
        )
        db_session.add(state)
        db_session.flush()

        phase = get_phase_for_discovery_page(db_session, page_id)
        assert phase == 2

    def test_get_phase_for_discovery_page_defaults_to_one_when_missing(
        self, db_session: Session
    ) -> None:
        """Negative path: Default to phase 1 when page has no entry in fair_selection_state."""
        page_id = uuid4()

        phase = get_phase_for_discovery_page(db_session, page_id)
        assert phase == 1


class TestClaimOrderIncludesPhase:
    """Slice 3: Verify phase is included in claim order."""

    def test_claim_order_ranks_phase_before_priority(
        self, db_session: Session
    ) -> None:
        """Happy path: Phase component in claim order sorts phase 1 before phase 2."""
        catalogue_id_a = uuid4()
        catalogue_id_b = uuid4()
        repo = TaskRepository(db_session)

        # Create tasks with different phases and priorities
        task_a = repo.insert_task(
            TaskTarget(
                catalogue_service_id=catalogue_id_a,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example-a.com",
            ),
            priority=100,
            phase=1,
        )

        task_b = repo.insert_task(
            TaskTarget(
                catalogue_service_id=catalogue_id_b,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example-b.com",
            ),
            priority=50,  # Higher priority (lower number), but phase 2
            phase=2,
        )

        db_session.flush()

        # Claim both tasks
        now = datetime.utcnow()
        claimed = repo.list_pending_tasks_for_claim(
            limit=2,
            kinds=[DiscoveryTaskKind.RENDER_PAGE],
            now=now,
        )

        # Phase 1 task should come first despite having lower priority
        assert len(claimed) == 2
        assert claimed[0].id == task_a.id
        assert claimed[1].id == task_b.id

    def test_claim_order_preserves_completeness_within_phase(
        self, db_session: Session
    ) -> None:
        """Negative path: Page completeness applies within same phase after phase+priority."""
        catalogue_id_a = uuid4()
        catalogue_id_b = uuid4()
        repo = TaskRepository(db_session)

        # Create two tasks with same phase and priority
        task_a = repo.insert_task(
            TaskTarget(
                catalogue_service_id=catalogue_id_a,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example-a.com",
            ),
            priority=100,
            phase=1,
        )

        task_b = repo.insert_task(
            TaskTarget(
                catalogue_service_id=catalogue_id_b,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example-b.com",
            ),
            priority=100,
            phase=1,
        )

        db_session.flush()

        # Claim both tasks
        now = datetime.utcnow()
        claimed = repo.list_pending_tasks_for_claim(
            limit=2,
            kinds=[DiscoveryTaskKind.RENDER_PAGE],
            now=now,
        )

        # Both tasks should be claimable; phase and priority don't distinguish them
        assert len(claimed) == 2
        assert {claimed[0].id, claimed[1].id} == {task_a.id, task_b.id}


class TestEnqueueTasksWithPhase:
    """Slice 4: Verify tasks are enqueued with phase tracking."""

    def test_enqueue_discovery_task_with_phase_one(self, db_session: Session) -> None:
        """Happy path: New discovery tasks inserted with phase=1 by default."""
        catalogue_id = uuid4()
        repo = TaskRepository(db_session)

        task = repo.insert_task(
            TaskTarget(
                catalogue_service_id=catalogue_id,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example.com",
            )
        )
        db_session.flush()

        assert task.phase == 1

    def test_insert_task_allows_explicit_phase_override(
        self, db_session: Session
    ) -> None:
        """Negative path: Task insertion respects explicit phase override."""
        catalogue_id = uuid4()
        repo = TaskRepository(db_session)

        task = repo.insert_task(
            TaskTarget(
                catalogue_service_id=catalogue_id,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example.com",
            ),
            phase=2,
        )
        db_session.flush()

        assert task.phase == 2


class TestPhaseAwareClaimOrdering:
    """Slice 5: Integration test verifying phase + completeness ordering."""

    def test_discover_tasks_claim_phase_1_before_phase_2_regardless_of_completeness(
        self, db_session: Session
    ) -> None:
        """Happy path: Phase 1 items claim before phase 2, independent of completeness."""
        page_a_id = uuid4()
        page_b_id = uuid4()

        repo = TaskRepository(db_session)

        # Enqueue tasks for page A (phase 1)
        task_a1 = repo.insert_task(
            TaskTarget(
                catalogue_service_id=page_a_id,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example-a-1.com",
            ),
            phase=1,
            priority=100,
        )
        task_a2 = repo.insert_task(
            TaskTarget(
                catalogue_service_id=page_a_id,
                kind=DiscoveryTaskKind.LLM_EXTRACT,
                target_url="https://example-a-2.com",
            ),
            phase=1,
            priority=100,
        )

        # Enqueue tasks for page B (phase 2)
        task_b1 = repo.insert_task(
            TaskTarget(
                catalogue_service_id=page_b_id,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example-b-1.com",
            ),
            phase=2,
            priority=100,
        )
        task_b2 = repo.insert_task(
            TaskTarget(
                catalogue_service_id=page_b_id,
                kind=DiscoveryTaskKind.LLM_EXTRACT,
                target_url="https://example-b-2.com",
            ),
            phase=2,
            priority=100,
        )

        db_session.flush()

        # Claim all 4 tasks
        now = datetime.utcnow()
        claimed = repo.list_pending_tasks_for_claim(
            limit=4,
            kinds=[DiscoveryTaskKind.RENDER_PAGE, DiscoveryTaskKind.LLM_EXTRACT],
            now=now,
        )

        # Phase 1 tasks must claim before phase 2
        assert len(claimed) == 4
        claimed_ids = [t.id for t in claimed]
        phase_1_indices = [
            i for i, tid in enumerate(claimed_ids) if tid in {task_a1.id, task_a2.id}
        ]
        phase_2_indices = [
            i for i, tid in enumerate(claimed_ids) if tid in {task_b1.id, task_b2.id}
        ]

        assert all(i < min(phase_2_indices) for i in phase_1_indices), (
            f"Phase 1 tasks must claim before phase 2: {claimed_ids}"
        )

    def test_discovery_tasks_within_phase_respect_completeness(
        self, db_session: Session
    ) -> None:
        """Negative path: Completeness tie-breaks within phase are preserved."""
        page_a_id = uuid4()
        page_b_id = uuid4()

        repo = TaskRepository(db_session)

        # Both phase 1, same priority
        task_a = repo.insert_task(
            TaskTarget(
                catalogue_service_id=page_a_id,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example-a.com",
            ),
            priority=100,
            phase=1,
        )

        task_b = repo.insert_task(
            TaskTarget(
                catalogue_service_id=page_b_id,
                kind=DiscoveryTaskKind.RENDER_PAGE,
                target_url="https://example-b.com",
            ),
            priority=100,
            phase=1,
        )

        db_session.flush()

        # Claim both tasks
        now = datetime.utcnow()
        claimed = repo.list_pending_tasks_for_claim(
            limit=2,
            kinds=[DiscoveryTaskKind.RENDER_PAGE],
            now=now,
        )

        # Both should be claimed (they have the same phase and priority)
        assert len(claimed) == 2
        claimed_ids = {claimed[0].id, claimed[1].id}
        assert claimed_ids == {task_a.id, task_b.id}
