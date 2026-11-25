---
id: C7
depends_on:
  - C1
  - C2
touches:
  - apps/api/app/features/discovery/repository/tasks.py
  - apps/api/app/features/discovery/repository/task_page_completeness.py
  - apps/api/app/models/discovery/discovery_task.py
  - tests/features/discovery/
execution: chapter-implementer
---

# C7: Update Discovery Task Selection

## Goal

Extend discovery task selection with a phase component, so phase-1 pages rank before phase-2 pages regardless of confidence. Discovery's existing page-completeness tie-break (D7) is preserved; phase ranking adds an additional layer above it.

## Acceptance Criteria

- ✅ Phase component added to discovery task priority formula
- ✅ Phase 1 items rank before phase 2 items (independent of any other factors)
- ✅ Page-completeness boost still applies as a secondary tie-break within each phase
- ✅ Discovery tasks inserted with phase=1 by default
- ✅ Claim order: `phase ASC, priority ASC, page_completeness DESC, created_at ASC, id ASC`
- ✅ No regression in existing page-completeness behavior

## Read first

- **00-architecture.md**: "Discovery" section (page 102–106) describes entity_id as `catalogue_service_id` and states that discovery already has page-completeness tie-break (D7); C7 extends it with phase ranking.
- **01-rollout.md**: C7 is part of Batch 2 (State Management & Pipeline Priorities); depends on C1 and C2 but not on other pipelines.

## Coordination scope

**Add:**

- Phase column to `DiscoveryTask` (nullable during migration, defaults to 1)
- Helper function: `get_phase_for_discovery_page(session, catalogue_service_id)` to read phase from `fair_selection_state`
- Updated `_claim_order()` to include phase component

**Edit:**

- `apps/api/app/features/discovery/repository/tasks.py`: Update `_claim_order()` and `list_pending_tasks_for_claim()`
- `apps/api/app/features/discovery/repository/task_page_completeness.py`: No change needed to completeness logic itself; phase is a separate ordering dimension
- `apps/api/app/models/discovery/discovery_task.py`: Add `phase` column (default 1)
- `apps/api/app/features/discovery/enqueue.py` (or task insertion entry point): Pass `phase` when creating new tasks

**Do not edit:**

- `app/models/fair_selection.py` (owned by C2)
- `app/features/discovery/repository/task_clauses.py` (owned by D7 decision; unaffected by phase)

## Work items

### Slice 1: Add Phase Column to DiscoveryTask Model

**Red**: Two tests:

1. **Happy path** (`test_discovery_task_has_phase_column`): `DiscoveryTask` model includes `phase` attribute
   - Create a `DiscoveryTask` with `phase=2`
   - Assert: `task.phase == 2` (readable)

2. **Negative path** (`test_discovery_task_phase_defaults_to_one`): Phase defaults to 1 when not specified
   - Create a `DiscoveryTask` without passing `phase` parameter
   - Assert: `task.phase == 1` (default applied)

**Green**: Update `apps/api/app/models/discovery/discovery_task.py`:

```python
# Add to DiscoveryTask class
phase: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
```

**Refactor**: Check that the column aligns with phase semantics elsewhere (1=breadth-first, 2=depth-first, 3=refresh). No extraction needed; single-line addition.

### Slice 2: Read Phase for Discovery Pages

**Red**: Two tests:

1. **Happy path** (`test_get_phase_for_discovery_page_reads_from_state`): Read phase from `fair_selection_state`
   - Setup: `FairSelectionState(pipeline='discovery', entity_id=page_id, phase=2)`
   - Call: `get_phase_for_discovery_page(session, page_id)` → returns 2
   - Assert: Correct phase read

2. **Negative path** (`test_get_phase_for_discovery_page_defaults_to_one_when_missing`): Missing phase entry returns default
   - Setup: No entry in `fair_selection_state` for page_id
   - Call: `get_phase_for_discovery_page(session, page_id)` → returns 1
   - Assert: Doesn't crash; assumes phase 1 (breadth-first)

**Green**: Add helper function to `apps/api/app/features/discovery/repository/tasks.py`:

```python
from uuid import UUID
from app.models.fair_selection import FairSelectionState
from sqlalchemy.orm import Session

def get_phase_for_discovery_page(session: Session, catalogue_service_id: UUID) -> int:
    """Read phase for a discovery page; default to phase 1 if not found.

    Discovery entity_id is catalogue_service_id (page).
    """
    state = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == 'discovery',
        FairSelectionState.entity_id == catalogue_service_id
    ).first()
    return state.phase if state else 1
```

**Refactor**: Check if `get_phases_for_discovery_pages()` (batch version) is needed; defer to Slice 4 if claim needs it. For now, keep single-page variant simple.

### Slice 3: Modify Claim Order to Include Phase

**Red**: Two tests:

1. **Happy path** (`test_claim_order_ranks_phase_before_priority`): Phase component in claim order sorts phase 1 before phase 2
   - Setup: Two tasks (phase=1, priority=100) and (phase=2, priority=50)
   - Call: Retrieve claim order → `_claim_order(page_completeness_expr)`
   - Assert: Order tuple includes phase as first dimension (before priority)
   - Assert: When both tasks are claimable, phase=1 task comes first (despite lower priority)

2. **Negative path** (`test_claim_order_preserves_completeness_within_phase`): Page completeness still applies as tie-break within phase
   - Setup: Two tasks (both phase=1, same priority), one page 60% complete, one 20% complete
   - Call: Retrieve claim order
   - Assert: Page-completeness DESC is applied after phase and priority (complete page claims first)
   - Assert: Completeness does NOT override phase

**Green**: Update `_claim_order()` in `apps/api/app/features/discovery/repository/tasks.py`:

```python
def _claim_order(page_completeness: ColumnElement) -> tuple[ColumnElement, ...]:
    """Return the claim order: phase, priority, page-completeness-desc, created_at, id.

    Phase (ASC) ensures breadth-first (phase 1) items claim before depth-first (phase 2).
    Within phase and priority, page-completeness-desc tie-breaks to claim pages nearing
    completion before emptier pages (original D7 logic, now under phase constraint).
    """
    return (
        DiscoveryTask.phase.asc(),
        DiscoveryTask.priority.asc(),
        func.coalesce(page_completeness, 0).desc(),
        DiscoveryTask.created_at.asc(),
        DiscoveryTask.id.asc(),
    )
```

**Refactor**: Verify that the tuple order matches the architecture (phase, priority, completeness, created_at, id). Check for any existing tests that assume old order; update assertion messages if needed. No extraction needed; tuple is the minimal representation.

### Slice 4: Enqueue Discovery Tasks with Phase

**Red**: Two tests:

1. **Happy path** (`test_enqueue_discovery_task_with_phase_one`): New discovery tasks inserted with phase=1
   - Setup: Page with no existing tasks
   - Call: Insert a new discovery task via entry point (e.g., `TaskRepository.insert_task()`)
   - Assert: Task created with `phase=1`

2. **Negative path** (`test_insert_task_allows_explicit_phase_override`): Task insertion can override default phase if needed
   - Call: `insert_task(..., phase=2)`
   - Assert: Task created with `phase=2` (optional parameter respected)

**Green**: Update `TaskRepository.insert_task()` in `apps/api/app/features/discovery/repository/tasks.py`:

```python
def insert_task(
    self,
    target: TaskTarget,
    *,
    priority: int = 100,
    phase: int = 1,  # New parameter, defaults to phase 1
) -> DiscoveryTask:
    """Insert a pending task for ``target`` with optional phase override."""
    task = DiscoveryTask(
        catalogue_service_id=target.catalogue_service_id,
        kind=target.kind,
        target_url=target.target_url,
        input_key=target.input_key,
        artifact_id=target.artifact_id,
        status=DiscoveryTaskStatus.PENDING,
        priority=priority,
        phase=phase,  # Pass phase through
    )
    self._session.add(task)
    self._session.flush()
    return task
```

**Refactor**: Check if any callers of `insert_task()` need to pass explicit phase (e.g., during re-enqueue for refresh). For now, default to 1 is correct; callers can override if needed. No extraction needed.

### Slice 5: Integration Test (Phase + Completeness Ordering)

**Red**: Two tests:

1. **Happy path** (`test_discover_tasks_claim_phase_1_before_phase_2_regardless_of_completeness`): Phase 1 items claim before phase 2, even if phase 2 page is more complete
   - Setup:
     - Page A (phase=1, 10% complete, 2 pending tasks)
     - Page B (phase=2, 90% complete, 2 pending tasks)
   - Call: `list_pending_tasks_for_claim(limit=4, ...)`
   - Assert: Returned tasks are [A-task1, A-task2, B-task1, B-task2] (all phase 1 before any phase 2)

2. **Negative path** (`test_discovery_tasks_within_phase_respect_completeness`): Page completeness still applies within same phase
   - Setup:
     - Page A (phase=1, 20% complete, 1 pending task)
     - Page B (phase=1, 60% complete, 1 pending task)
     - Both same priority
   - Call: `list_pending_tasks_for_claim(limit=1, ...)`
   - Assert: Returned task is Page B (more complete, same phase/priority)

**Green**: Write integration test file `tests/features/discovery/test_phase_aware_claim_order.py`:

```python
import pytest
from datetime import datetime
from uuid import uuid4

from app.models.discovery import DiscoveryTask, DiscoveryTaskStatus, DiscoveryTaskKind
from app.features.discovery.repository.tasks import TaskRepository
from app.features.fair_selection import FairSelectionState
from sqlalchemy.orm import Session


@pytest.fixture
def db_session(test_session: Session):
    """Provide a test database session."""
    return test_session


def test_discover_tasks_claim_phase_1_before_phase_2_regardless_of_completeness(
    db_session: Session,
):
    """Phase 1 items claim before phase 2, even if phase 2 page is more complete."""
    # Setup pages
    page_a_id = uuid4()
    page_b_id = uuid4()

    # Enqueue tasks for page A (phase 1, low completeness)
    repo = TaskRepository(db_session)
    task_a1 = repo.insert_task(
        TaskTarget(catalogue_service_id=page_a_id, kind=DiscoveryTaskKind.RENDER_PAGE, ...),
        phase=1,
    )
    task_a2 = repo.insert_task(
        TaskTarget(catalogue_service_id=page_a_id, kind=DiscoveryTaskKind.LLM_EXTRACT, ...),
        phase=1,
    )

    # Enqueue tasks for page B (phase 2, high completeness)
    task_b1 = repo.insert_task(
        TaskTarget(catalogue_service_id=page_b_id, kind=DiscoveryTaskKind.RENDER_PAGE, ...),
        phase=2,
    )
    task_b2 = repo.insert_task(
        TaskTarget(catalogue_service_id=page_b_id, kind=DiscoveryTaskKind.LLM_EXTRACT, ...),
        phase=2,
    )

    # Setup completeness: page B is more complete (but phase 2)
    # (Insert mock completeness data via test helper or directly)

    # Claim
    now = datetime.utcnow()
    claimed = repo.list_pending_tasks_for_claim(
        limit=4,
        kinds=[DiscoveryTaskKind.RENDER_PAGE, DiscoveryTaskKind.LLM_EXTRACT],
        now=now,
    )

    # Assert: phase 1 tasks claim before phase 2, regardless of completeness
    claimed_ids = [t.id for t in claimed]
    phase_1_indices = [i for i, tid in enumerate(claimed_ids) if tid in {task_a1.id, task_a2.id}]
    phase_2_indices = [i for i, tid in enumerate(claimed_ids) if tid in {task_b1.id, task_b2.id}]

    assert all(i < min(phase_2_indices) for i in phase_1_indices), (
        f"Phase 1 tasks must claim before phase 2: {claimed_ids}"
    )


def test_discovery_tasks_within_phase_respect_completeness(db_session: Session):
    """Page completeness still applies within same phase."""
    page_a_id = uuid4()
    page_b_id = uuid4()

    repo = TaskRepository(db_session)

    # Both phase 1, same priority
    task_a = repo.insert_task(
        TaskTarget(catalogue_service_id=page_a_id, ...),
        priority=100,
        phase=1,
    )
    task_b = repo.insert_task(
        TaskTarget(catalogue_service_id=page_b_id, ...),
        priority=100,
        phase=1,
    )

    # Setup completeness: page B is more complete
    # (Insert mock completeness data)

    now = datetime.utcnow()
    claimed = repo.list_pending_tasks_for_claim(limit=1, kinds=[...], now=now)

    # Assert: page B (more complete) claims first
    assert claimed[0].id == task_b.id, (
        f"Within phase 1 and priority 100, task from more-complete page should claim first: {claimed[0].id} vs {task_b.id}"
    )
```

**Refactor**: Check test helper functions for mocking completeness; extract if setup is repeated. Align test names and assertions with TDD red/green format. For now, test structure is clear; defer optimization until actual implementation reveals duplication.

## Test Output

**After this chapter**:

- `DiscoveryTask` model includes `phase` column (default 1, nullable=False)
- `apps/api/app/features/discovery/repository/tasks.py`:
  - New function: `get_phase_for_discovery_page(session, catalogue_service_id) -> int`
  - Updated `_claim_order()` to include `DiscoveryTask.phase.asc()` as first dimension
  - Updated `TaskRepository.insert_task()` to accept optional `phase` parameter
- Test file: `tests/features/discovery/test_phase_aware_claim_order.py` (5 test functions covering all slices)

## Tests or document checks

| Check | Happy path | Negative path |
|-------|-----------|---|
| Phase column | `test_discovery_task_has_phase_column` | `test_discovery_task_phase_defaults_to_one` |
| Read phase | `test_get_phase_for_discovery_page_reads_from_state` | `test_get_phase_for_discovery_page_defaults_to_one_when_missing` |
| Claim order | `test_claim_order_ranks_phase_before_priority` | `test_claim_order_preserves_completeness_within_phase` |
| Enqueue | `test_enqueue_discovery_task_with_phase_one` | `test_insert_task_allows_explicit_phase_override` |
| Integration | `test_discover_tasks_claim_phase_1_before_phase_2_regardless_of_completeness` | `test_discovery_tasks_within_phase_respect_completeness` |

## Review gate

Before merging:

1. ✅ All 10 tests pass: `pytest tests/features/discovery/test_phase_aware_claim_order.py -v`
2. ✅ Narrow gate passes: `pytest tests/features/discovery/` (verify no regression in existing discovery tests)
3. ✅ Lint & format: `ruff check apps/api/app/features/discovery/ && ruff format --check apps/api/app/features/discovery/`
4. ✅ Type check: `mypy apps/api/app/features/discovery/repository/tasks.py` (phase parameter type-safe)
5. ✅ Refactor checklist walked for `_claim_order()`, `TaskRepository.insert_task()`, and `get_phase_for_discovery_page()` (see Refactor Report below)

## Out of scope

- Phase transition logic (owned by C3: "Implement State Transition Logic")
- Fair selection state table design (owned by C2: "Create `fair_selection_state` Table")
- Discovery metrics emission (owned by C9: "Add Observability & Metrics")
- End-to-end discovery workflow testing (owned by C10: "Integration & Validation")

## Verification

```bash
# Run from repository root.

# Narrow gate: discovery tests only
pytest tests/features/discovery/test_phase_aware_claim_order.py -v

# Full discovery test suite (verify no regression)
pytest tests/features/discovery/ -v

# Lint & format
ruff check apps/api/app/features/discovery/
ruff format --check apps/api/app/features/discovery/

# Type check (if mypy configured for the project)
mypy apps/api/app/features/discovery/repository/tasks.py
```

Expected: All tests pass (10 green), no lint/format issues, no type errors.

## Refactor Report

### Refactor Pass: `_claim_order()` and `TaskRepository`

**Scope**: `_claim_order()` function, `TaskRepository.insert_task()`, and new `get_phase_for_discovery_page()` helper.

**Checklist**:

- [ ] **~5 LOC** per function/method
  - `_claim_order()`: 7 lines (tuple of 5 order clauses). **At limit but acceptable**; each clause is minimal and the tuple is the right shape. No extraction needed.
  - `get_phase_for_discovery_page()`: 6 lines (query + return). **At limit**; straightforward read with single fallback. No extraction needed.
  - `insert_task()`: 10 lines before refactor (8 lines after adding phase parameter). **Within bounds**; simple constructor + add + flush. No extraction needed.

- [ ] **~100 LOC** per class
  - `TaskRepository`: Already exists; no change to class-level scope. Phase parameter addition is local to `insert_task()`.

- [ ] **Single concern** per unit
  - `_claim_order()`: Returns ordering tuple for discovery claim. ✅ Single concern (ordering).
  - `get_phase_for_discovery_page()`: Reads phase from database with default fallback. ✅ Single concern (lookup + default).
  - `insert_task()`: Constructs and persists a `DiscoveryTask`. ✅ Single concern (insertion).

- [ ] **Rule of three** (branches/arms)
  - `_claim_order()`: No branching; pure tuple construction. ✅ No extraction needed.
  - `get_phase_for_discovery_page()`: One conditional (`if state else 1`). ✅ Minimal; no extraction needed.
  - `insert_task()`: No branching; constructor call. ✅ No extraction needed.

- [ ] **One nesting level**
  - All functions are flat (no nested loops, no nested if/try). ✅ No extraction needed.

- [ ] **Dispatch only** in match/switch
  - No match statements in these functions. ✅ N/A.

- [ ] **Duplication**
  - `_claim_order()` is now specialized to discovery (not shared with translation or embedding). ✅ No duplication introduced.
  - `get_phase_for_discovery_page()` follows same pattern as `get_phase_for_candidate()` from C4; both query `FairSelectionState` with pipeline-specific filter. This is intentional per-pipeline lookup; no over-abstraction needed yet (would require 3+ similar functions to trigger extraction).

- [ ] **Boolean parameters**
  - No boolean parameters in these functions. ✅ N/A.

- [ ] **Data clumps**
  - `insert_task()` constructs `DiscoveryTask` with 8 fields. This is the proper DTO; no data clump issue. ✅ Existing design is sound.

- [ ] **Names**
  - `_claim_order()`: Clearly returns ordering for claim. ✅
  - `get_phase_for_discovery_page()`: Clearly reads phase for a page. ✅
  - `insert_task()`: Clearly inserts a task. ✅

- [ ] **Types** per type-hinting.mdc
  - `_claim_order(page_completeness: ColumnElement) -> tuple[ColumnElement, ...]`: ✅ Precise return type.
  - `get_phase_for_discovery_page(session: Session, catalogue_service_id: UUID) -> int`: ✅ All parameters and return typed strictly.
  - `insert_task(..., phase: int = 1) -> DiscoveryTask`: ✅ Phase parameter typed as int (1–3).

- [ ] **Docstrings** per docstrings.mdc
  - `_claim_order()`: Updated docstring explains phase ordering. ✅
  - `get_phase_for_discovery_page()`: Docstring documents fallback behavior. ✅
  - `insert_task()`: Updated docstring mentions phase parameter. ✅

**Outcome**: ✅ No refactor needed beyond adding phase parameter. Functions are already minimal, single-concern, and unduplicatd within discovery. When other pipelines (C4, C5, C6) are complete, C8 will centralize phase-aware claim ordering in `LeasedQueue.claim()`; until then, discovery-specific ordering is appropriate.

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`. Pull it only if it tracks an upstream.
- Create the chapter branch with `git checkout -b feat/c7-discovery-phase`.
- Commit the red tests first (Slices 1–5), then the green implementation (Slices 1–5).
- Run the local gate on the chapter branch: `pytest tests/features/discovery/test_phase_aware_claim_order.py && ruff check apps/api/app/features/discovery/ && ruff format --check apps/api/app/features/discovery/`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
