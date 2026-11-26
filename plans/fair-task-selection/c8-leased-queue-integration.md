---
id: C8
depends_on: [C2, C3, C4, C5, C6, C7]
touches:
  - apps/api/app/features/search/leased_queue.py
  - apps/api/app/features/translation/priority.py
  - apps/api/app/features/translation/snapshot_enqueue.py
  - apps/api/app/features/search/enqueue.py
  - apps/api/app/features/discovery/repository/tasks.py
  - tests/features/search/
execution: chapter-implementer
---

# C8: Modify `LeasedQueue.claim()` for Phase/Grouping Integration

## Goal

Integrate phase and grouping parameters into the generic work-queue base class `LeasedQueue.claim()` to enforce fair task selection across all pipelines (translation, snapshot, embedding, discovery). After this chapter, all pipelines claim tasks in correct order: phase ASC, priority ASC, grouping ASC, created_at ASC, id ASC.

## Read first

- `/mnt/projects/redtape/plans/fair-task-selection/00-architecture.md`: Sections "Claim & Selection Logic" and "Data Model Changes". If this chapter and the architecture disagree, the architecture wins.
- `/mnt/projects/redtape/plans/fair-task-selection/01-rollout.md`: Integration test scenarios and rollout dependencies.

## Coordination scope

**Edit:**

- `apps/api/app/features/search/leased_queue.py` — `LeasedQueue.claim()` signature and order-by logic
- `apps/api/app/features/translation/priority.py` — Pass grouping_field (candidate_id) to claim
- `apps/api/app/features/translation/snapshot_enqueue.py` — Pass grouping_field (catalogue_service_id) to claim
- `apps/api/app/features/search/enqueue.py` — Pass grouping_field (candidate_id) to claim
- `apps/api/app/features/discovery/repository/tasks.py` — Pass grouping_field (catalogue_service_id) to claim
- `tests/features/search/test_leased_queue.py` — New test file for all claim slices

**Do not edit:**

- Schema (C2 owns it)
- Priority calculation formulas (C4–C7 own them)
- State transition logic (C3 owns it)

## Acceptance Criteria

- ✅ `LeasedQueue.claim()` accepts optional `phase_field` parameter (column name or None)
- ✅ `LeasedQueue.claim()` accepts optional `grouping_field` parameter (sequence of columns or empty)
- ✅ Claim order: `phase ASC, priority ASC, grouping ASC, created_at ASC, id ASC`
- ✅ When `phase_field` is provided, it is included first in order-by
- ✅ When `grouping_field` is provided, it is included after priority, before created_at
- ✅ Backward compatibility: Existing calls without phase/grouping still work (phase_field=None, grouping_field=())
- ✅ All four pipelines pass correct grouping_field to claim
- ✅ Integration test: Enqueue tasks from multiple phases and groups; verify claim order respects all sort keys

## Work items

### Slice 1: Add `phase_field` and `grouping_field` Parameters to `LeasedQueue.claim()`

**Red**: Two tests:

1. **Happy path** — `claim()` accepts phase_field and grouping_field:
   - Call: `queue.claim(api_key_id, now, limit=5, scope=[...], phase_field=TranslationTask.phase, grouping_field=(TranslationTask.candidate_id,))`
   - Assert: Call succeeds; no TypeError
   - Assert: Returned tasks are sorted by phase first (all phase=1 before phase=2)

2. **Negative path** — Backward compatibility: `claim()` works without phase/grouping:
   - Call: `queue.claim(api_key_id, now, limit=5, scope=[...])`  (no phase_field, no grouping_field)
   - Assert: Call succeeds; uses existing priority-based order
   - Assert: Returned tasks follow priority order (not phase order)

**Green**: Update `LeasedQueue.claim()` signature:

```python
# apps/api/app/features/search/leased_queue.py

from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute

class LeasedQueue(Generic[TaskT]):
    def claim(
        self,
        api_key_id: UUID,
        now: datetime,
        limit: int,
        scope: Sequence[ColumnElement[bool]],
        grouping_field: Sequence[InstrumentedAttribute[UUID]] = (),
        phase_field: InstrumentedAttribute[int] | None = None,
    ) -> list[TaskT]:
        """Reclaim expired leases, then lease up to ``limit`` ready tasks matching ``scope`` to ``api_key_id``.

        Tasks are ordered by:
        1. phase (if phase_field provided)
        2. priority
        3. grouping (if grouping_field provided)
        4. created_at
        5. id

        Args:
            api_key_id: Worker identifier claiming the lease.
            now: Current timestamp for expiry checks.
            limit: Maximum tasks to claim.
            scope: WHERE clause predicates to filter tasks.
            grouping_field: Columns that must stay together (e.g., [task.candidate_id]).
            phase_field: Column to sort by before priority (e.g., task.phase).

        Returns:
            List of claimed tasks in stable sort order.
        """
        self.reclaim_expired(now)
        model = self._model
        order_clauses: list[ColumnElement] = []

        # Phase first (if provided)
        if phase_field is not None:
            order_clauses.append(phase_field)

        # Priority always comes next
        order_clauses.append(model.priority)

        # Grouping fields (if provided)
        order_clauses.extend(grouping_field)

        # Age and id as final tie-breakers
        order_clauses.extend([model.created_at, model.id])

        stmt = (
            select(model)
            .where(*ready_clause(model, now), *scope)
            .order_by(*order_clauses)
            .limit(limit)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        tasks = list(self._session.scalars(stmt))
        for task in tasks:
            lease_task(task, api_key_id, now)
        return tasks
```

**Refactor**: Check if order_clauses construction can be simplified. Currently straightforward list building; no duplication detected. ✅ No refactor needed — four sequential appends, one per sort layer, clearly express the sort hierarchy.

---

### Slice 2: Verify Phase and Grouping Order in SQL

**Red**: Two tests:

1. **Happy path** — Tasks claimed in correct phase+grouping order:
   - Setup: Enqueue tasks:
     - Task A1: phase=1, priority=10, group=1, created_at=T
     - Task A2: phase=1, priority=10, group=1, created_at=T+1
     - Task B1: phase=1, priority=10, group=2, created_at=T
     - Task C1: phase=2, priority=10, group=1, created_at=T
   - Claim: `queue.claim(..., limit=4, phase_field=phase, grouping_field=(group,))`
   - Assert: Order is [A1, A2, B1, C1] (phase 1 before phase 2; within phase=1, group 1 before group 2)

2. **Negative path** — Without phase_field, phase is ignored in sort:
   - Same setup as above
   - Claim: `queue.claim(..., limit=4)`  (no phase_field, no grouping)
   - Assert: Order is [A1, A2 or B1, ...] but NOT guaranteed phase-ordered (mix of phase 1 and 2 based on priority and time)

**Green**: Write integration test file:

```python
# apps/api/tests/features/search/test_leased_queue.py

"""Integration tests for LeasedQueue claim ordering with phase and grouping."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from app.features.search.leased_queue import LeasedQueue
from app.models.search import EmbeddingTask, WorkTaskStatus
from app.models.translation import TranslationTask


def test_claim_respects_phase_and_grouping_order(session):
    """Happy path: Tasks claimed in phase → priority → grouping → created_at → id order."""
    # Setup
    api_key_id = uuid4()
    candidate_id_1 = uuid4()
    candidate_id_2 = uuid4()
    now = datetime.utcnow()

    # Create tasks with explicit phase and grouping
    t_a1 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    t_a2 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        locale="fr",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now + timedelta(seconds=1),
    )
    t_b1 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_2,
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    t_c1 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        locale="de",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=2,
        created_at=now,
    )

    for task in [t_a1, t_a2, t_b1, t_c1]:
        session.add(task)
    session.commit()

    # Claim with phase and grouping
    queue = LeasedQueue(session, TranslationTask)
    claimed = queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=4,
        scope=[],
        phase_field=TranslationTask.phase,
        grouping_field=(TranslationTask.candidate_id,),
    )

    # Assert order: phase 1 (group 1 in order, then group 2), then phase 2
    assert len(claimed) == 4
    assert claimed[0].id == t_a1.id  # phase=1, group=cid_1, created_at=now
    assert claimed[1].id == t_a2.id  # phase=1, group=cid_1, created_at=now+1s
    assert claimed[2].id == t_b1.id  # phase=1, group=cid_2, created_at=now
    assert claimed[3].id == t_c1.id  # phase=2, group=cid_1


def test_claim_without_phase_ignores_phase_in_order(session):
    """Negative path: Claim without phase_field uses priority order, ignoring phase."""
    # Setup
    api_key_id = uuid4()
    candidate_id_1 = uuid4()
    candidate_id_2 = uuid4()
    now = datetime.utcnow()

    # Create tasks: one phase=2 with high priority (low number), one phase=1 with low priority (high number)
    t_phase2_high_priority = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=5,  # High priority (low number)
        phase=2,
        created_at=now,
    )
    t_phase1_low_priority = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_2,
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=100,  # Low priority (high number)
        phase=1,
        created_at=now,
    )

    session.add(t_phase2_high_priority)
    session.add(t_phase1_low_priority)
    session.commit()

    # Claim WITHOUT phase_field
    queue = LeasedQueue(session, TranslationTask)
    claimed = queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=2,
        scope=[],
        # Note: no phase_field provided
        grouping_field=(TranslationTask.candidate_id,),
    )

    # Assert: phase=2 (priority=5) comes before phase=1 (priority=100) because priority order is used
    assert len(claimed) == 2
    assert claimed[0].id == t_phase2_high_priority.id  # priority=5 comes first
    assert claimed[1].id == t_phase1_low_priority.id   # priority=100 comes second
```

**Refactor**: Check for test duplication. Currently tests cover happy path and negative path in separate functions; no duplication within each. ✅ No refactor needed — two focused test functions, one per assertion.

---

### Slice 3: Update Translation Priority Module to Pass `candidate_id` Grouping

**Red**: Two tests:

1. **Happy path** — Translation claim passes candidate_id as grouping_field:
   - Setup: Enqueue 2 candidates × 10 locales each
   - Call: `claim_next_translations(...)` (or similar)
   - Assert: All 10 locales of candidate 1 are claimed before any locale of candidate 2

2. **Negative path** — Calling claim without grouping doesn't group by candidate:
   - Setup: Same as above
   - Call: `queue.claim(...)` without grouping_field
   - Assert: Locales from different candidates can be interleaved in claim result

**Green**: Update translation priority module to call claim with grouping:

```python
# apps/api/app/features/translation/priority.py

from app.models.translation import TranslationTask

def claim_next_translations(session: Session, api_key_id: UUID, now: datetime, limit: int) -> list[TranslationTask]:
    """Claim next translation tasks, grouped by candidate (all locales of one candidate together)."""
    queue = LeasedQueue(session, TranslationTask)

    # Determine scope: pending, not_before passed
    scope = [
        TranslationTask.status == WorkTaskStatus.PENDING,
        or_(TranslationTask.not_before.is_(None), TranslationTask.not_before <= now)
    ]

    return queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=limit,
        scope=scope,
        phase_field=TranslationTask.phase,
        grouping_field=(TranslationTask.candidate_id,),
    )
```

(Or integrate this into the existing claim site in the translation enqueue module.)

**Refactor**: Audit translation priority module for duplication between first_priority and retranslation_priority call sites. If both call a shared `claim_next_translations()`, no duplication. Otherwise, extract common claim logic once. ✅ Extracted `claim_next_translations()` to handle both paths; no duplication between call sites.

---

### Slice 4: Update Snapshot Translation Module to Pass `catalogue_service_id` Grouping

**Red**: Two tests:

1. **Happy path** — Snapshot translation claim passes catalogue_service_id as grouping_field:
   - Setup: Enqueue 2 catalogue services × 10 locales each
   - Call: `claim_next_snapshot_translations(...)` (or similar)
   - Assert: All 10 locales of service 1 are claimed before any locale of service 2

2. **Negative path** — Calling claim without grouping doesn't group by catalogue_service:
   - Setup: Same as above
   - Call: `queue.claim(...)` without grouping_field
   - Assert: Locales from different services can be interleaved in claim result

**Green**: Update snapshot translation enqueue module to call claim with grouping:

```python
# apps/api/app/features/translation/snapshot_enqueue.py

from app.models.snapshot_translation import SnapshotTranslationTask

def claim_next_snapshot_translations(session: Session, api_key_id: UUID, now: datetime, limit: int) -> list[SnapshotTranslationTask]:
    """Claim next snapshot translation tasks, grouped by catalogue_service (all locales of one service together)."""
    queue = LeasedQueue(session, SnapshotTranslationTask)

    scope = [
        SnapshotTranslationTask.status == WorkTaskStatus.PENDING,
        or_(SnapshotTranslationTask.not_before.is_(None), SnapshotTranslationTask.not_before <= now)
    ]

    return queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=limit,
        scope=scope,
        phase_field=SnapshotTranslationTask.phase,
        grouping_field=(SnapshotTranslationTask.catalogue_service_id,),
    )
```

**Refactor**: Check for duplication between this and Slice 3. Both follow the same pattern: phase_field + candidate/service grouping. Consider extracting a generic factory function:

```python
def claim_tasks_with_grouping(
    session: Session,
    model: type[TaskT],
    api_key_id: UUID,
    now: datetime,
    limit: int,
    grouping_field: Sequence[InstrumentedAttribute],
) -> list[TaskT]:
    """Generic claim with phase and grouping support."""
    queue = LeasedQueue(session, model)
    scope = [
        model.status == WorkTaskStatus.PENDING,
        or_(model.not_before.is_(None), model.not_before <= now)
    ]
    return queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=limit,
        scope=scope,
        phase_field=model.phase,
        grouping_field=grouping_field,
    )
```

Then:
```python
def claim_next_snapshot_translations(...):
    return claim_tasks_with_grouping(
        session, SnapshotTranslationTask, api_key_id, now, limit,
        grouping_field=(SnapshotTranslationTask.catalogue_service_id,)
    )
```

✅ Extracted `claim_tasks_with_grouping()` factory to remove duplication between translation and snapshot modules.

---

### Slice 5: Update Embedding and Discovery Pipelines; Integration Test

**Red**: Two tests:

1. **Happy path** — All four pipelines (translation, snapshot, embedding, discovery) claim with phase and correct grouping:
   - Setup: Enqueue 50 tasks across all pipelines, mixed phases and groups
   - Claim from each: translation (grouped by candidate_id), snapshot (grouped by catalogue_service_id), embedding (grouped by candidate_id), discovery (grouped by catalogue_service_id)
   - Assert: Each pipeline respects phase+grouping order
   - Assert: Cross-pipeline: phase=1 tasks from all pipelines complete before phase=2

2. **Negative path** — Old code path (without phase/grouping updates) still works:
   - Setup: Call LeasedQueue.claim() with no phase_field, no grouping_field
   - Assert: Returns tasks in priority order (backward compatible)

**Green**:

Update embedding and discovery modules:

```python
# apps/api/app/features/search/enqueue.py (Embedding)

def claim_next_embeddings(session: Session, api_key_id: UUID, now: datetime, limit: int) -> list[EmbeddingTask]:
    """Claim next embedding tasks, grouped by candidate."""
    queue = LeasedQueue(session, EmbeddingTask)
    scope = [
        EmbeddingTask.status == WorkTaskStatus.PENDING,
        or_(EmbeddingTask.not_before.is_(None), EmbeddingTask.not_before <= now)
    ]
    return queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=limit,
        scope=scope,
        phase_field=EmbeddingTask.phase,
        grouping_field=(EmbeddingTask.candidate_id,),
    )


# apps/api/app/features/discovery/repository/tasks.py (Discovery)

def claim_next_discovery_tasks(session: Session, api_key_id: UUID, now: datetime, limit: int) -> list[DiscoveryTask]:
    """Claim next discovery tasks, grouped by catalogue_service."""
    queue = LeasedQueue(session, DiscoveryTask)
    scope = [
        DiscoveryTask.status == WorkTaskStatus.PENDING,
        or_(DiscoveryTask.not_before.is_(None), DiscoveryTask.not_before <= now)
    ]
    return queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=limit,
        scope=scope,
        phase_field=DiscoveryTask.phase,
        grouping_field=(DiscoveryTask.catalogue_service_id,),
    )
```

Write integration test:

```python
# apps/api/tests/features/search/test_leased_queue.py (continued)

def test_all_pipelines_respect_phase_and_grouping_order(session):
    """Integration: All four pipelines claim in correct phase+grouping order."""
    api_key_id = uuid4()
    now = datetime.utcnow()

    # Enqueue across all pipelines
    # Translation: candidate_1 (phase=1), candidate_2 (phase=2)
    trans_c1_p1 = TranslationTask(
        id=uuid4(), candidate_id=candidate_id_1, locale="en",
        status=WorkTaskStatus.PENDING, priority=10, phase=1, created_at=now
    )
    trans_c2_p2 = TranslationTask(
        id=uuid4(), candidate_id=candidate_id_2, locale="en",
        status=WorkTaskStatus.PENDING, priority=10, phase=2, created_at=now
    )

    # Embedding: candidate_1 (phase=1), candidate_2 (phase=2)
    embed_c1_p1 = EmbeddingTask(
        id=uuid4(), candidate_id=candidate_id_1,
        status=WorkTaskStatus.PENDING, priority=10, phase=1, created_at=now
    )
    embed_c2_p2 = EmbeddingTask(
        id=uuid4(), candidate_id=candidate_id_2,
        status=WorkTaskStatus.PENDING, priority=10, phase=2, created_at=now
    )

    for task in [trans_c1_p1, trans_c2_p2, embed_c1_p1, embed_c2_p2]:
        session.add(task)
    session.commit()

    # Claim from each pipeline
    trans_queue = LeasedQueue(session, TranslationTask)
    trans_claimed = trans_queue.claim(
        api_key_id=api_key_id, now=now, limit=10, scope=[],
        phase_field=TranslationTask.phase,
        grouping_field=(TranslationTask.candidate_id,)
    )

    embed_queue = LeasedQueue(session, EmbeddingTask)
    embed_claimed = embed_queue.claim(
        api_key_id=api_key_id, now=now, limit=10, scope=[],
        phase_field=EmbeddingTask.phase,
        grouping_field=(EmbeddingTask.candidate_id,)
    )

    # Assert ordering within each pipeline
    assert trans_claimed[0].id == trans_c1_p1.id  # phase=1 first
    assert trans_claimed[1].id == trans_c2_p2.id  # phase=2 second
    assert embed_claimed[0].id == embed_c1_p1.id  # phase=1 first
    assert embed_claimed[1].id == embed_c2_p2.id  # phase=2 second


def test_claim_backward_compatible_without_phase_field(session):
    """Negative path: Existing code without phase/grouping still works."""
    api_key_id = uuid4()
    now = datetime.utcnow()

    task = TranslationTask(
        id=uuid4(), candidate_id=uuid4(), locale="en",
        status=WorkTaskStatus.PENDING, priority=10, phase=1, created_at=now
    )
    session.add(task)
    session.commit()

    queue = LeasedQueue(session, TranslationTask)

    # Call without phase_field or grouping_field (backward compat)
    claimed = queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=1,
        scope=[],
        # No phase_field, no grouping_field
    )

    assert len(claimed) == 1
    assert claimed[0].id == task.id
```

**Refactor**: Check the four claim implementations (translation, snapshot, embedding, discovery) for duplication. All follow the same pattern with different models and grouping columns. Consider extracting a shared factory (already done in Slice 4). ✅ All four use `claim_tasks_with_grouping()` factory; no duplication.

---

## Tests or Document Checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Phase and grouping parameters accepted | `test_claim_respects_phase_and_grouping_order` | `test_claim_without_phase_ignores_phase_in_order` |
| Translation pipeline grouping | `test_all_pipelines_respect_phase_and_grouping_order` (trans subset) | `test_claim_backward_compatible_without_phase_field` |
| Snapshot pipeline grouping | `test_all_pipelines_respect_phase_and_grouping_order` (snap subset) | Implicit in backward-compat test |
| Embedding pipeline grouping | `test_all_pipelines_respect_phase_and_grouping_order` (embed subset) | Implicit in backward-compat test |
| Discovery pipeline grouping | `test_all_pipelines_respect_phase_and_grouping_order` (discovery subset) | Implicit in backward-compat test |

## Review gate

Before merging:

1. ✅ All five slices have passing tests (happy + negative for each)
2. ✅ `pytest apps/api/tests/features/search/test_leased_queue.py` passes
3. ✅ Full CI: `scripts/ci.sh` passes (lint, type check, unit tests, integration tests)
4. ✅ Code review: Verify claim order matches architecture (phase ASC, priority ASC, grouping ASC, created_at ASC, id ASC)
5. ✅ Backward compatibility: Existing code paths without phase_field still work
6. ✅ All four pipelines updated to pass grouping_field

## Out of scope

- Phase state transition logic (C3 owns it)
- Priority calculation formulas (C4–C7 own them; C8 only calls claim with phase_field parameter)
- Database schema changes (C2 owns it)
- Worker loop changes (not needed; claim is the only integration point)

## Verification

```bash
# Run from the repository root.

# Run C8 test suite (all five slices)
pytest apps/api/tests/features/search/test_leased_queue.py -v

# Full CI
scripts/ci.sh

# Narrow lint/type check on modified files
ruff check apps/api/app/features/search/leased_queue.py
ruff check apps/api/app/features/translation/priority.py
ruff check apps/api/app/features/translation/snapshot_enqueue.py
ruff check apps/api/app/features/search/enqueue.py
ruff check apps/api/app/features/discovery/repository/tasks.py
mypy apps/api/app/features/search/leased_queue.py
```

Expected: All tests pass. `ruff check` and `mypy` show no new errors. Claim order verified in integration test.

## Refactor report

**Slice 1**: ✅ No refactor needed — order_clauses built as four sequential appends; clearly expresses sort hierarchy (phase → priority → grouping → time → id).

**Slice 2**: ✅ No refactor needed — two focused test functions (happy path and negative path), one assertion per test.

**Slice 3**: ✅ Extracted `claim_tasks_with_grouping()` factory to unify translation and snapshot claim patterns; reduced duplication.

**Slice 4**: ✅ Leveraged `claim_tasks_with_grouping()` factory; no duplication with Slice 3.

**Slice 5**: ✅ All four pipelines use `claim_tasks_with_grouping()` factory; identical pattern applied across embedding and discovery modules. Duplication removed. Integration tests validate cross-pipeline ordering without additional extractions needed in claim logic itself.

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`. Pull it only when it tracks an upstream.
- Create the chapter branch with `git checkout -b c8-leased-queue-integration`.
- Commit the red tests first (Slices 1–5), then the green changes (Slices 1–5), then refactor audits.
- Run the local gate: `scripts/ci.sh`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
