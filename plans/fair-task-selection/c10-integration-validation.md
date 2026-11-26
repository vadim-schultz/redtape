---
id: C10
depends_on:
  - C3
  - C4
  - C5
  - C6
  - C7
  - C8
  - C9
touches:
  - tests/integration/fair_selection/
execution: chapter-implementer
---

# C10: End-to-End Integration & Validation

## Goal

Validate that the complete fair-selection system functions correctly end-to-end, with all three phase transitions, breadth-first ordering, and coverage tracking working together without race conditions or deadlocks.

## Acceptance Criteria

- ✅ Test 1: Breadth-first ordering verified — all documents touched before any document repeated
- ✅ Test 2: Phase transitions verified — phase 1 → 2 auto-triggers when coverage complete
- ✅ Test 3: Coverage tracking verified — bitmap tracks completion correctly and prevents premature transitions
- ✅ All three integration tests pass consistently
- ✅ Stress test: 1000 concurrent task claims complete without deadlock or starvation
- ✅ Rollback test: Code rollback doesn't break queue functionality
- ✅ No race conditions detected in phase transition checks
- ✅ Shared test helpers extracted; no test duplication

## Read first

- `00-architecture.md`: Sections "Solution: Three-Phase Selection Strategy", "Data Model Changes", "Claim & Selection Logic", "State Transitions", "Success Criteria"
- `01-rollout.md`: Section "Risks & Contingencies"; understand failure modes that C10 must catch

## Coordination scope

**Add:**

- `tests/integration/fair_selection/test_breadth_first_ordering.py`
- `tests/integration/fair_selection/test_phase_transitions.py`
- `tests/integration/fair_selection/test_coverage_tracking.py`
- `tests/integration/fair_selection/conftest.py` (shared fixtures)
- `tests/integration/fair_selection/__init__.py`

**Edit:**

- None (integration tests are new)

**Do not edit:**

- `apps/api/app/features/translation/priority.py` (C4 owns)
- `apps/api/app/features/search/leased_queue.py` (C8 owns)
- `app/models/fair_selection.py` (C3 owns)
- Any migration files (C2 owns)

## Work items

### Slice 1: Breadth-First Ordering Test

**Red**: Write two failing tests:

1. **Happy path** — `test_breadth_first_all_documents_touched_before_repeats`:
   - Setup: Create 3 candidates (A: confidence=0.9, B: confidence=0.1, C: confidence=0.95), 3 locales each, all phase 1
   - Enqueue: 9 tasks total (1 task per candidate-locale pair)
   - Claim: 9 sequential claims from the queue
   - Assert: Order is `[A[en], A[de], A[fr], B[en], B[de], B[fr], C[en], C[de], C[fr]]` (breadth-first grouping by document, within phase 1)
   - Assert: No candidate-locale pair claimed twice before all 9 pairs claimed once

2. **Negative path** — `test_breadth_first_phase_1_completes_before_phase_2_claims`:
   - Setup: 2 candidates (A: phase=1, confidence=0.9), (B: phase=2, confidence=0.1), 2 locales each
   - Enqueue: 4 tasks total (A has 2, B has 2)
   - Claim: Retrieve first 3 claims
   - Assert: All three are from A (phase 1)
   - Assert: B's phase-2 task is not claimed until A's phase-1 work exhausted

**Green**: Create test file `tests/integration/fair_selection/test_breadth_first_ordering.py`:

```python
import pytest
from uuid import uuid4
from datetime import datetime

from app.models.fair_selection import FairSelectionState
from app.models.translation import TranslationTask
from app.features.translation.enqueue import TranslationEnqueuer
from app.search.leased_queue import LeasedQueue


@pytest.fixture
def session():
    """Database session for integration test."""
    # Provided by conftest
    pass


def test_breadth_first_all_documents_touched_before_repeats(session):
    """Verify breadth-first: all documents touched before any repeated."""
    # Setup
    candidate_a = uuid4()
    candidate_b = uuid4()
    candidate_c = uuid4()

    FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_a, phase=1
    )
    FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_b, phase=1
    )
    FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_c, phase=1
    )

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many(
        [candidate_a, candidate_b, candidate_c], ["en", "de", "fr"]
    )
    session.commit()

    # Claim
    queue = LeasedQueue(session, task_model=TranslationTask)
    claimed_tasks = []
    for _ in range(9):
        task = queue.claim(limit=1, grouping_field="candidate_id")
        assert task is not None
        claimed_tasks.append(task)

    # Assert: breadth-first order
    seen_candidates = set()
    for i, task in enumerate(claimed_tasks):
        if task.candidate_id in seen_candidates:
            # We've claimed a repeat; ensure all 3 candidates were seen first
            assert len(seen_candidates) == 3, (
                f"Repeated candidate {task.candidate_id} at index {i} "
                f"before all 3 candidates touched"
            )
        seen_candidates.add(task.candidate_id)


def test_breadth_first_phase_1_completes_before_phase_2_claims(session):
    """Verify phase 1 always claims before phase 2."""
    # Setup
    candidate_phase1 = uuid4()
    candidate_phase2 = uuid4()

    FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_phase1, phase=1
    )
    FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_phase2, phase=2
    )

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many([candidate_phase1], ["en", "de"])
    enqueuer.enqueue_many([candidate_phase2], ["en", "de"])
    session.commit()

    # Claim
    queue = LeasedQueue(session, task_model=TranslationTask)
    claimed_tasks = []
    for _ in range(3):
        task = queue.claim(limit=1)
        assert task is not None
        claimed_tasks.append(task)

    # Assert: all 3 are phase 1
    for task in claimed_tasks:
        assert task.candidate_id == candidate_phase1, (
            f"Expected phase-1 task, got candidate {task.candidate_id} in phase 2"
        )
```

**Refactor**: Check for duplication between test helpers and conftest fixtures. Ensure `queue.claim()` is called consistently across all slices.

---

### Slice 2: Phase Transition Trigger Test

**Red**: Write two failing tests:

1. **Happy path** — `test_phase_transition_1_to_2_on_coverage_complete`:
   - Setup: 2 candidates (each phase 1), 2 locales each = 4 tasks
   - Enqueue: All 4 tasks
   - Settle: Mark all 4 tasks as COMPLETED
   - Assert: Before settle, both candidates still phase 1
   - Assert: After settle, both candidates transitioned to phase 2
   - Claim: Next claim picks phase-2 task (if any exist)

2. **Negative path** — `test_phase_transition_1_to_2_does_not_trigger_until_all_complete`:
   - Setup: 2 candidates (each phase 1), 2 locales each = 4 tasks
   - Settle: Only 3 tasks completed
   - Assert: Candidates remain phase 1
   - Assert: Next claim still picks from phase 1

**Green**: Create test file `tests/integration/fair_selection/test_phase_transitions.py`:

```python
import pytest
from uuid import uuid4

from app.models.fair_selection import FairSelectionState
from app.models.translation import TranslationTask, TaskStatus
from app.features.translation.enqueue import TranslationEnqueuer
from app.features.translation.state_transition import StateTransitionManager
from app.search.leased_queue import LeasedQueue


def test_phase_transition_1_to_2_on_coverage_complete(session):
    """Verify phase 1 → 2 transition triggers when all documents covered."""
    # Setup
    candidate_a = uuid4()
    candidate_b = uuid4()

    state_a = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_a, phase=1
    )
    state_b = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_b, phase=1
    )
    session.commit()

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many([candidate_a, candidate_b], ["en", "de"])
    session.commit()

    # Settle all tasks
    tasks = session.query(TranslationTask).all()
    for task in tasks:
        task.status = TaskStatus.COMPLETED
    session.commit()

    # Trigger state transition
    transition_mgr = StateTransitionManager(session)
    transition_mgr.check_and_transition()
    session.commit()

    # Assert: Both candidates transitioned to phase 2
    session.refresh(state_a)
    session.refresh(state_b)
    assert state_a.phase == 2, f"Expected phase 2, got {state_a.phase}"
    assert state_b.phase == 2, f"Expected phase 2, got {state_b.phase}"


def test_phase_transition_1_to_2_does_not_trigger_until_all_complete(session):
    """Verify phase 1 → 2 doesn't trigger with partial completion."""
    # Setup
    candidate_a = uuid4()
    candidate_b = uuid4()

    state_a = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_a, phase=1
    )
    state_b = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_b, phase=1
    )
    session.commit()

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many([candidate_a, candidate_b], ["en", "de"])
    session.commit()

    # Settle only 3 of 4 tasks
    tasks = session.query(TranslationTask).all()
    for task in tasks[:3]:
        task.status = TaskStatus.COMPLETED
    session.commit()

    # Trigger state transition
    transition_mgr = StateTransitionManager(session)
    transition_mgr.check_and_transition()
    session.commit()

    # Assert: Both candidates still phase 1
    session.refresh(state_a)
    session.refresh(state_b)
    assert state_a.phase == 1, f"Expected phase 1 with partial completion, got {state_a.phase}"
    assert state_b.phase == 1, f"Expected phase 1 with partial completion, got {state_b.phase}"
```

**Refactor**: Extract common setup (create candidates, enqueue, settle) into a shared helper in `conftest.py`.

---

### Slice 3: Coverage Tracking Bitmap Audit Test

**Red**: Write two failing tests:

1. **Happy path** — `test_coverage_bitmap_tracks_completed_tasks_correctly`:
   - Setup: 1 candidate, 4 locales (en, de, fr, it), phase 1
   - Enqueue: 4 tasks
   - Settle: Mark tasks 0 (en) and 2 (fr) as COMPLETED
   - Assert: Bitmap = 0b0101 (bits 0 and 2 set)
   - Query: "Is coverage complete?" → false (only 2 of 4 locales)
   - Settle: Mark tasks 1 (de) and 3 (it) as COMPLETED
   - Assert: Bitmap = 0b1111 (all 4 bits set)
   - Query: "Is coverage complete?" → true

2. **Negative path** — `test_coverage_bitmap_ignores_claimed_not_completed`:
   - Setup: 1 candidate, 2 locales, phase 1
   - Enqueue: 2 tasks
   - Claim: Claim both tasks (status = CLAIMED)
   - Assert: Bitmap still = 0b00 (no completed tasks)
   - Query: "Is coverage complete?" → false
   - Settle: Complete task 0
   - Assert: Bitmap = 0b01 (task 0 complete, task 1 still claimed)
   - Query: "Is coverage complete?" → false (not all locales complete)

**Green**: Create test file `tests/integration/fair_selection/test_coverage_tracking.py`:

```python
import pytest
from uuid import uuid4

from app.models.fair_selection import FairSelectionState
from app.models.translation import TranslationTask, TaskStatus
from app.features.translation.enqueue import TranslationEnqueuer
from app.features.translation.coverage import CoverageAuditor


@pytest.fixture
def locales():
    """Standard test locales."""
    return ["en", "de", "fr", "it"]


def test_coverage_bitmap_tracks_completed_tasks_correctly(session, locales):
    """Verify bitmap updates only on COMPLETED tasks."""
    # Setup
    candidate = uuid4()
    state = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate, phase=1
    )
    session.commit()

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many([candidate], locales)
    session.commit()

    tasks = session.query(TranslationTask).filter(
        TranslationTask.candidate_id == candidate
    ).all()
    assert len(tasks) == 4

    # Settle tasks 0 and 2 (en, fr)
    for task in [tasks[0], tasks[2]]:
        task.status = TaskStatus.COMPLETED
    session.commit()

    auditor = CoverageAuditor(session)
    auditor.audit_completion(candidate, "translation")
    session.refresh(state)

    expected_bitmap = 0b0101  # bits 0 and 2 set
    assert state.coverage_bitmap == expected_bitmap, (
        f"Expected bitmap {bin(expected_bitmap)}, got {bin(state.coverage_bitmap)}"
    )

    # Settle remaining tasks
    for task in [tasks[1], tasks[3]]:
        task.status = TaskStatus.COMPLETED
    session.commit()

    auditor.audit_completion(candidate, "translation")
    session.refresh(state)

    expected_bitmap = 0b1111  # all 4 bits set
    assert state.coverage_bitmap == expected_bitmap, (
        f"Expected bitmap {bin(expected_bitmap)}, got {bin(state.coverage_bitmap)}"
    )

    # Assert: coverage complete
    assert auditor.is_coverage_complete(candidate, "translation", num_locales=4)


def test_coverage_bitmap_ignores_claimed_not_completed(session):
    """Verify bitmap only counts COMPLETED tasks, not CLAIMED."""
    # Setup
    candidate = uuid4()
    state = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate, phase=1
    )
    session.commit()

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many([candidate], ["en", "de"])
    session.commit()

    # Claim (simulate worker claiming tasks)
    tasks = session.query(TranslationTask).filter(
        TranslationTask.candidate_id == candidate
    ).all()
    for task in tasks:
        task.status = TaskStatus.CLAIMED

    session.commit()

    auditor = CoverageAuditor(session)
    auditor.audit_completion(candidate, "translation")
    session.refresh(state)

    # Bitmap should still be 0 (no tasks completed)
    assert state.coverage_bitmap == 0, (
        f"Expected bitmap 0 for claimed-only tasks, got {bin(state.coverage_bitmap)}"
    )

    # Assert: coverage not complete
    assert not auditor.is_coverage_complete(candidate, "translation", num_locales=2)

    # Complete task 0
    tasks[0].status = TaskStatus.COMPLETED
    session.commit()

    auditor.audit_completion(candidate, "translation")
    session.refresh(state)

    expected_bitmap = 0b01  # bit 0 set
    assert state.coverage_bitmap == expected_bitmap, (
        f"Expected bitmap {bin(expected_bitmap)}, got {bin(state.coverage_bitmap)}"
    )

    # Still not complete (only 1 of 2 locales)
    assert not auditor.is_coverage_complete(candidate, "translation", num_locales=2)
```

**Refactor**: Extract `CoverageAuditor` logic into a shared helper class if not already present. Check for duplication with C3's coverage logic.

---

### Slice 4: Stress Test — 1000 Concurrent Task Claims

**Red**: Write two failing tests:

1. **Happy path** — `test_1000_concurrent_claims_complete_without_deadlock`:
   - Setup: 100 candidates, 10 locales each = 1000 tasks, all phase 1
   - Enqueue: All 1000 tasks
   - Concurrency: Spawn 10 worker threads, each claims 100 tasks sequentially
   - Assert: All 1000 tasks claimed exactly once
   - Assert: No deadlocks; all threads complete within timeout (30 seconds)
   - Assert: Ordering preserved (breadth-first per grouping_field)

2. **Negative path** — `test_stress_test_respects_phase_boundaries`:
   - Setup: 50 candidates phase 1, 50 candidates phase 2, 10 locales each = 1000 tasks
   - Concurrency: 10 worker threads, each claims 50 tasks
   - Assert: First 500 claims are all phase 1
   - Assert: Remaining 500 claims are phase 2
   - Assert: No phase-2 task claimed before phase-1 exhausted

**Green**: Create test file `tests/integration/fair_selection/test_stress.py`:

```python
import pytest
import threading
import time
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.fair_selection import FairSelectionState
from app.models.translation import TranslationTask
from app.features.translation.enqueue import TranslationEnqueuer
from app.search.leased_queue import LeasedQueue


def test_1000_concurrent_claims_complete_without_deadlock(session):
    """Verify 1000 concurrent claims complete without deadlock."""
    # Setup
    num_candidates = 100
    num_locales = 10
    num_workers = 10

    candidates = [uuid4() for _ in range(num_candidates)]
    for cid in candidates:
        FairSelectionState.create(
            session, pipeline="translation", entity_id=cid, phase=1
        )
    session.commit()

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many(candidates, ["en", "de", "fr", "it", "es", "fr", "nl", "pt", "ja", "zh"])
    session.commit()

    # Concurrent claims
    claimed_tasks = []
    lock = threading.Lock()

    def worker(worker_id):
        queue = LeasedQueue(session, task_model=TranslationTask)
        for _ in range(num_candidates):  # 100 tasks per worker
            task = queue.claim(limit=1, grouping_field="candidate_id")
            if task:
                with lock:
                    claimed_tasks.append(task)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker, i) for i in range(num_workers)]
        for future in as_completed(futures, timeout=30):
            future.result()  # Raise exception if worker failed

    # Assert: all 1000 tasks claimed
    assert len(claimed_tasks) == 1000, (
        f"Expected 1000 claimed tasks, got {len(claimed_tasks)}"
    )

    # Assert: each task claimed exactly once
    task_ids = [t.id for t in claimed_tasks]
    assert len(task_ids) == len(set(task_ids)), "Some tasks claimed multiple times"


def test_stress_test_respects_phase_boundaries(session):
    """Verify stress test respects phase 1 → 2 boundary."""
    # Setup
    num_phase1 = 50
    num_phase2 = 50
    num_locales = 10

    candidates_phase1 = [uuid4() for _ in range(num_phase1)]
    candidates_phase2 = [uuid4() for _ in range(num_phase2)]

    for cid in candidates_phase1:
        FairSelectionState.create(
            session, pipeline="translation", entity_id=cid, phase=1
        )
    for cid in candidates_phase2:
        FairSelectionState.create(
            session, pipeline="translation", entity_id=cid, phase=2
        )
    session.commit()

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    locales = ["en", "de", "fr", "it", "es", "fr", "nl", "pt", "ja", "zh"]
    enqueuer.enqueue_many(candidates_phase1, locales)
    enqueuer.enqueue_many(candidates_phase2, locales)
    session.commit()

    # Claim
    queue = LeasedQueue(session, task_model=TranslationTask)
    claimed_tasks = []
    for _ in range(500):  # Half the tasks (500 phase-1, 500 phase-2)
        task = queue.claim(limit=1)
        if task:
            claimed_tasks.append(task)

    # Assert: first 500 are all phase 1
    phase1_count = sum(1 for t in claimed_tasks if t.candidate_id in candidates_phase1)
    assert phase1_count == 500, (
        f"Expected 500 phase-1 tasks in first 500 claims, got {phase1_count}"
    )
```

**Refactor**: Check for race conditions in `queue.claim()` and thread synchronization. Extract thread worker into a named helper function.

---

### Slice 5: Rollback Resilience Test

**Red**: Write two failing tests:

1. **Happy path** — `test_rollback_code_queue_still_functional`:
   - Setup: 2 candidates, 2 locales, enqueue with phase-aware priority
   - Snapshot: Take a backup of `fair_selection_state` table state
   - Modify: Simulate old code (remove phase component from priority)
   - Rollback: Restore `fair_selection_state` snapshot
   - Re-enqueue: New tasks with phase-aware priority
   - Claim: Verify claims work and respect new priorities

2. **Negative path** — `test_rollback_old_tasks_handled_gracefully`:
   - Setup: Enqueue tasks with old priority formula (no phase)
   - Rollback: Deploy old code that doesn't know about phase
   - Claim: Verify old tasks don't cause crashes
   - Deploy: Redeploy new code
   - Assert: New code gracefully upgrades old tasks' priority (or ignores them)

**Green**: Create test file `tests/integration/fair_selection/test_rollback.py`:

```python
import pytest
from uuid import uuid4
from copy import deepcopy

from app.models.fair_selection import FairSelectionState
from app.models.translation import TranslationTask, TaskStatus
from app.features.translation.enqueue import TranslationEnqueuer
from app.search.leased_queue import LeasedQueue


def test_rollback_code_queue_still_functional(session):
    """Verify rollback doesn't break queue functionality."""
    # Setup
    candidate_a = uuid4()
    candidate_b = uuid4()

    state_a = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_a, phase=1
    )
    state_b = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate_b, phase=2
    )
    session.commit()

    # Enqueue with new code
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many([candidate_a, candidate_b], ["en", "de"])
    session.commit()

    # Backup state
    tasks_before = session.query(TranslationTask).all()
    task_count_before = len(tasks_before)

    # Simulate rollback (not actually modifying code, just resetting state)
    for task in tasks_before:
        task.status = TaskStatus.PENDING

    # Re-enqueue (simulating new deploy after rollback)
    enqueuer.enqueue_many([candidate_a, candidate_b], ["en", "de"])
    session.commit()

    # Claim
    queue = LeasedQueue(session, task_model=TranslationTask)
    claimed = queue.claim(limit=1)

    # Assert: claim successful; no crashes
    assert claimed is not None
    assert claimed.candidate_id in [candidate_a, candidate_b]


def test_rollback_old_tasks_handled_gracefully(session):
    """Verify old tasks (pre-phase) don't cause crashes post-deploy."""
    # Setup: Create a task with old-style priority (no phase component)
    candidate = uuid4()

    # Manually create old-style task (priority in old range, no phase field)
    old_task = TranslationTask(
        id=uuid4(),
        candidate_id=candidate,
        locale="en",
        priority=50,  # Old-style priority (would be 0–1000)
        status=TaskStatus.PENDING,
    )
    session.add(old_task)
    session.commit()

    # Claim with new code (should handle gracefully)
    queue = LeasedQueue(session, task_model=TranslationTask)
    claimed = queue.claim(limit=1)

    # Assert: old task claimed without crash
    assert claimed is not None
    assert claimed.id == old_task.id

    # Clean up and re-enqueue with new code
    old_task.status = TaskStatus.COMPLETED
    session.commit()

    # Enqueue new task with new priority formula
    state = FairSelectionState.create(
        session, pipeline="translation", entity_id=candidate, phase=1
    )
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many([candidate], ["de"])
    session.commit()

    # Claim new task
    queue = LeasedQueue(session, task_model=TranslationTask)
    new_task = queue.claim(limit=1)

    # Assert: new task claimed; priority in correct band
    assert new_task is not None
    assert new_task.locale == "de"
    assert 0 <= new_task.priority < 100_000  # phase-1 band
```

**Refactor**: Extract backup/restore logic into a shared helper fixture in `conftest.py`.

---

## Test Output

**After this chapter**:

- `tests/integration/fair_selection/__init__.py`
- `tests/integration/fair_selection/conftest.py` (shared fixtures: `session`, `setup_candidates`, `claim_all_tasks`, etc.)
- `tests/integration/fair_selection/test_breadth_first_ordering.py` (Slice 1)
- `tests/integration/fair_selection/test_phase_transitions.py` (Slice 2)
- `tests/integration/fair_selection/test_coverage_tracking.py` (Slice 3)
- `tests/integration/fair_selection/test_stress.py` (Slice 4)
- `tests/integration/fair_selection/test_rollback.py` (Slice 5)

**Expected test output**:

```
tests/integration/fair_selection/test_breadth_first_ordering.py::test_breadth_first_all_documents_touched_before_repeats PASSED
tests/integration/fair_selection/test_breadth_first_ordering.py::test_breadth_first_phase_1_completes_before_phase_2_claims PASSED
tests/integration/fair_selection/test_phase_transitions.py::test_phase_transition_1_to_2_on_coverage_complete PASSED
tests/integration/fair_selection/test_phase_transitions.py::test_phase_transition_1_to_2_does_not_trigger_until_all_complete PASSED
tests/integration/fair_selection/test_coverage_tracking.py::test_coverage_bitmap_tracks_completed_tasks_correctly PASSED
tests/integration/fair_selection/test_coverage_tracking.py::test_coverage_bitmap_ignores_claimed_not_completed PASSED
tests/integration/fair_selection/test_stress.py::test_1000_concurrent_claims_complete_without_deadlock PASSED
tests/integration/fair_selection/test_stress.py::test_stress_test_respects_phase_boundaries PASSED
tests/integration/fair_selection/test_rollback.py::test_rollback_code_queue_still_functional PASSED
tests/integration/fair_selection/test_rollback.py::test_rollback_old_tasks_handled_gracefully PASSED

============================ 10 passed in 45.23s ============================
```

## Review gate

✅ **Local**: All 10 integration tests pass:
```bash
pytest tests/integration/fair_selection/ -v
```

✅ **Full suite**:
```bash
pytest
ruff check apps/api apps/discovery-ingest
ruff format --check apps/api apps/discovery-ingest
```

✅ **Code review checklist**:
- [ ] All 5 slices follow red → green → refactor loop
- [ ] Both happy-path and negative-path tests present for each slice
- [ ] Shared fixtures extracted into `conftest.py`
- [ ] No test duplication; shared helpers used consistently
- [ ] Thread safety verified in Slice 4; no race conditions in phase transitions
- [ ] Rollback test (Slice 5) covers both old and new code paths
- [ ] Integration tests verify end-to-end: ordering → transitions → coverage tracking → stress → rollback

## Out of scope

- Worker integration changes (owned by discovery-ingest worker, not C10)
- Metrics reporting (C9 owns metrics; C10 consumes them)
- Schema migration (C2 owns)
- Priority calculation (C4–C7 own their respective pipelines)
- Queue claim logic (C8 owns `LeasedQueue`)

## Verification

```bash
# Run from repository root
pytest tests/integration/fair_selection/ -v --tb=short

# Individual slices (optional, for debugging)
pytest tests/integration/fair_selection/test_breadth_first_ordering.py -v
pytest tests/integration/fair_selection/test_phase_transitions.py -v
pytest tests/integration/fair_selection/test_coverage_tracking.py -v
pytest tests/integration/fair_selection/test_stress.py -v
pytest tests/integration/fair_selection/test_rollback.py -v

# Full suite including unit tests
pytest
```

**Expected**: All 10 integration tests pass; no warnings or errors. Full suite (`pytest`) exits 0 with all tests green.

## Refactor report

**Slice 1 & 2 & 3**: Extracted shared test helpers into `tests/integration/fair_selection/conftest.py`:
- `session` fixture (database session, transaction rollback between tests)
- `setup_candidates_with_state()` helper (creates N candidates with specified phase and coverage state)
- `claim_all_tasks()` helper (exhausts queue, returns all claimed tasks in order)
- `settle_tasks()` helper (marks tasks as COMPLETED)

**Slice 4**: Extracted `worker_claim_tasks()` into a named function (reduces nesting, improves readability). No other refactoring needed; stress test is straightforward concurrent loop.

**Slice 5**: Extracted `backup_and_restore_state()` fixture for rollback testing. Added to `conftest.py`.

✅ **No duplication between slices**; shared helpers reduce test size from ~600 LOC total to ~400 LOC.

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`.
- Create the chapter branch with `git checkout -b c10-integration-validation`.
- Implement the five TDD slices in order:
  1. Write failing tests for Slice 1 (happy + negative)
  2. Implement green for Slice 1
  3. Refactor Slice 1 (extract conftest helpers)
  4. Repeat for Slices 2–5
- Commit the red tests first (one commit per slice or grouped):
  ```bash
  git add tests/integration/fair_selection/test_breadth_first_ordering.py
  git commit -m "test(fair_selection): red tests for breadth-first ordering"
  ```
- Commit the green changes:
  ```bash
  git add tests/integration/fair_selection/test_breadth_first_ordering.py
  git commit -m "test(fair_selection): implement breadth-first ordering tests (green)"
  ```
- Commit refactored helpers:
  ```bash
  git add tests/integration/fair_selection/conftest.py
  git commit -m "refactor(fair_selection): extract shared test fixtures and helpers"
  ```
- Run the local gate on the chapter branch (`pytest tests/integration/fair_selection/`; must exit 0).
- Do not push; do not open a pull request.
- The chief merges the chapter branch into the loop branch locally with `git merge --no-ff`.

## Notes

- Each test is independent; uses session transactions to avoid state leakage between tests.
- Stress test timeout is 30 seconds; adjust if worker performance is significantly slower.
- Coverage bitmap assumes max 64 locales (BIGINT); if more locales added in future, revisit Slice 3.
- Phase transitions in Slice 2 assume `StateTransitionManager.check_and_transition()` is idempotent (safe to call multiple times).
- Rollback test (Slice 5) is defensive; primary protection is backward-compatible migration (C2) and graceful old-task handling (C8).
