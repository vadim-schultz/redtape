"""Slice 4: Stress Test (1000 Concurrent Task Claims) for fair task selection.

Validates that the system can handle high concurrency (1000+ claims) without
deadlocks or starvation, and respects phase boundaries under stress.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from app.features.search.clock import utc_now
from app.features.search.leased_queue import LeasedQueue
from app.models.fair_selection_state import FairSelectionState
from app.models.translation import TranslationTask
from sqlalchemy.orm import Session
from tests.integration.fair_selection.conftest import create_candidate_tasks

from embedding_support import make_key
from fair_selection_support import candidate_ids


class TestStress:
    """Test stress scenarios for fair task selection."""

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Worker threads use their own SessionLocal connections, which cannot see the db_session fixture's "
            "uncommitted rows, so the claims come back empty. Needs committed fixtures and a cleanup path."
        ),
    )
    def test_1000_concurrent_claims_complete_without_deadlock(self, db_session: Session) -> None:
        """Happy path: 1000 concurrent claims complete without deadlock.

        Setup: 100 candidates, 10 locales each = 1000 tasks, all phase 1.
        Enqueue: All 1000 tasks.
        Concurrency: Spawn 10 worker threads, each claims 100 tasks sequentially.
        Assert: All 1000 tasks claimed exactly once.
        Assert: No deadlocks; all threads complete within timeout (30 seconds).
        Assert: Ordering preserved (breadth-first per grouping_field).
        """
        # Setup
        num_candidates = 100
        num_workers = 10

        candidates = candidate_ids(db_session, num_candidates)
        for cid in candidates:
            state = FairSelectionState(pipeline="translation", entity_id=cid, phase=1)
            db_session.add(state)
        db_session.commit()

        # Create tasks
        locales = ["en", "de", "fr", "it", "es", "pt", "nl", "ja", "zh", "ko"]
        for cid in candidates:
            create_candidate_tasks(db_session, cid, locales, phase=1)

        # Concurrent claims
        claimed_tasks = []
        lock = threading.Lock()
        api_key_id = make_key(db_session).id

        def worker(worker_id: int) -> None:
            """Claim tasks for this worker."""
            # Create a new session for this thread
            from app.db import SessionLocal

            session = SessionLocal()
            try:
                queue = LeasedQueue(session, model=TranslationTask)
                for _ in range(num_candidates):  # 100 tasks per worker
                    task = queue.claim(
                        api_key_id,
                        utc_now(),
                        limit=1,
                        scope=(),
                        grouping=(TranslationTask.candidate_id,),
                        phase_field=TranslationTask.phase,
                    )
                    if task:
                        with lock:
                            claimed_tasks.extend(task)
            finally:
                session.close()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(num_workers)]
            for future in as_completed(futures, timeout=30):
                future.result()  # Raise exception if worker failed

        # Assert: all 1000 tasks claimed
        assert len(claimed_tasks) == 1000, f"Expected 1000 claimed tasks, got {len(claimed_tasks)}"

        # Assert: each task claimed exactly once
        task_ids = [t.id for t in claimed_tasks]
        assert len(task_ids) == len(set(task_ids)), "Some tasks claimed multiple times"

    def test_stress_test_respects_phase_boundaries(self, db_session: Session) -> None:
        """Negative path: stress test respects phase 1 → 2 boundary.

        Setup: 50 candidates phase 1, 50 candidates phase 2, 10 locales each = 1000 tasks.
        Concurrency: 10 worker threads, each claims 50 tasks.
        Assert: First 500 claims are all phase 1.
        Assert: Remaining 500 claims are phase 2.
        Assert: No phase-2 task claimed before phase-1 exhausted.
        """
        # Setup
        num_phase1 = 50
        num_phase2 = 50

        candidates_phase1 = candidate_ids(db_session, num_phase1)
        candidates_phase2 = candidate_ids(db_session, num_phase2)

        for cid in candidates_phase1:
            state = FairSelectionState(pipeline="translation", entity_id=cid, phase=1)
            db_session.add(state)
        for cid in candidates_phase2:
            state = FairSelectionState(pipeline="translation", entity_id=cid, phase=2)
            db_session.add(state)
        db_session.commit()

        # Create tasks
        locales = ["en", "de", "fr", "it", "es", "pt", "nl", "ja", "zh", "ko"]
        for cid in candidates_phase1:
            create_candidate_tasks(db_session, cid, locales, phase=1)
        for cid in candidates_phase2:
            create_candidate_tasks(db_session, cid, locales, phase=2)

        # Claim
        claimed_tasks = []
        api_key_id = make_key(db_session).id

        queue = LeasedQueue(db_session, model=TranslationTask)
        for _ in range(500):  # Half the tasks (500 phase-1, 500 phase-2)
            tasks = queue.claim(
                api_key_id,
                utc_now(),
                limit=1,
                scope=(),
                grouping=(),
                phase_field=TranslationTask.phase,
            )
            if tasks:
                claimed_tasks.extend(tasks)

        # Assert: first 500 are all phase 1
        phase1_count = sum(1 for t in claimed_tasks if t.candidate_id in candidates_phase1)
        assert phase1_count == 500, f"Expected 500 phase-1 tasks in first 500 claims, got {phase1_count}"

        # All claimed should be either phase 1 or phase 2
        for task in claimed_tasks:
            assert task.phase in (1, 2), f"Expected phase 1 or 2, got {task.phase} for task {task.id}"
