---
id: C6
depends_on:
  - C1
  - C2
touches:
  - apps/api/app/features/search/enqueue.py
  - apps/api/app/features/search/repository.py
  - apps/api/app/models/search.py
  - tests/features/search/
execution: chapter-implementer
---

# C6: Update Embedding Priority & Phase Tracking

**Depends on:** C1, C2 · **Architecture:** 00-architecture.md (Embedding section) · **Rollout:** 01-rollout.md

## Goal

Apply the phase-state framework to the embedding pipeline. Embeddings have uniform priority within redtape (always 100), but need phase component added for consistency. Add phase tracking to `EmbeddingTask`; track when all candidates have embeddings in all locales (phase 1 → 2 trigger).

## Read first

- **00-architecture.md**: Embedding section, Phase → Phase transitions, State Transitions
- **01-rollout.md**: Migration path, schema changes

## Coordination scope

**Add:**

- `apps/api/app/features/search/phase.py` — phase-aware priority calculation and phase state queries for embeddings

**Edit:**

- `apps/api/app/models/search.py` — add `phase` column to `EmbeddingTask`
- `apps/api/app/features/search/enqueue.py` — set initial phase=1 on new embeddings
- `apps/api/app/features/search/repository.py` — query phase state; track coverage bitmap on settlement
- `apps/api/app/features/search/task_settle.py` — update coverage bitmap when embedding task completes
- Database migration (new column `embedding_task.phase`)

**Do not edit:**

- `apps/api/app/features/search/leased_queue.py` (generic claim logic, owned by C8)
- `apps/api/app/features/search/complete.py` (settlement dispatch, owned by C9)
- State transition checks (owned by C3)

## Work items

### Slice 1: Read Phase for Embedding Task

**Red**: Two tests:

1. **Happy path** — `test_get_phase_for_embedding_candidate_found`:
   - Setup: `FairSelectionState(pipeline='embedding', entity_id=candidate_id, phase=2)`
   - Call: `get_phase_for_embedding(session, candidate_id)` → returns 2
   - Assert: Correct phase read from state table

2. **Negative path** — `test_get_phase_for_embedding_candidate_missing`:
   - Setup: No entry in `fair_selection_state` for candidate_id (new candidate)
   - Call: `get_phase_for_embedding(session, candidate_id)` → returns 1
   - Assert: Defaults to phase 1 (breadth-first); doesn't crash

**Green**: Add helper in `apps/api/app/features/search/phase.py`:

```python
"""Phase-aware priority and state tracking for embeddings."""

from uuid import UUID
from sqlalchemy.orm import Session
from app.models.fair_selection import FairSelectionState


def get_phase_for_embedding(session: Session, candidate_id: UUID) -> int:
    """Read phase for a candidate's embedding; default to phase 1 if not found."""
    state = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == 'embedding',
        FairSelectionState.entity_id == candidate_id
    ).first()
    return state.phase if state else 1
```

**Refactor**: No duplication yet (single function, single concern).

---

### Slice 2: Add Phase Component to Priority

**Red**: Two tests:

1. **Happy path** — `test_embedding_phase_affects_priority`:
   - Scenario: Candidate A (phase=1) vs. Candidate B (phase=2)
   - Calculate: `embedding_priority(phase=1)` vs. `embedding_priority(phase=2)`
   - Assert: Phase 1 priority < Phase 2 priority (phase 1 claims first)
   - Assert: Both within expected bands (phase 1: 0–99,999; phase 2: 100,000–199,999)

2. **Negative path** — `test_embedding_uniform_within_phase`:
   - Scenario: Two candidates A and B, both phase=1
   - Calculate: `embedding_priority(phase=1)` for both
   - Assert: Priority values are identical (embeddings are uniform within phase; no confidence ranking)

**Green**: Add priority formula to `apps/api/app/features/search/phase.py`:

```python
def embedding_priority(phase: int = 1) -> int:
    """
    Calculate priority for an embedding task.

    Priority bands by phase:
      phase=1: 0–99,999 (breadth-first)
      phase=2: 100,000–199,999 (depth-first)
      phase=3: 200,000–299,999 (refresh)

    Within phase, all embeddings have the same priority (uniform distribution).
    """
    phase_band = (phase - 1) * 100_000
    return phase_band + 100  # constant offset; no confidence ranking
```

**Refactor**: Check if `_phase_band()` helper from C4 is reusable across search and translation modules. Extract to shared utility if used in multiple places; otherwise, keep inline here (single call site).

---

### Slice 3: Set Initial Phase on New Embeddings

**Red**: Two tests:

1. **Happy path** — `test_enqueue_embedding_sets_phase_1`:
   - Setup: Call `EmbeddingEnqueuer(session, model="default", locales=["en", "de"]).enqueue(candidate_id, built_text)`
   - Assert: New `EmbeddingTask` created with `phase=1`
   - Assert: Priority reflects phase 1 band (0–99,999)

2. **Negative path** — `test_enqueue_embedding_does_not_override_existing_phase`:
   - Setup: `EmbeddingTask(candidate_id, status=PENDING, phase=2)` already exists
   - Action: Call enqueue with updated `built_text` (hash changed)
   - Assert: Task is re-upserted with phase **unchanged** (stays 2, doesn't reset to 1)
   - Assert: `upsert` does not set phase column (no update to phase)

**Green**: Update `EmbeddingEnqueuer._upsert_pending()` in `apps/api/app/features/search/enqueue.py`:

```python
def _upsert_pending(self, candidate_id: UUID, built: BuiltText) -> bool:
    """Upsert a pending embedding task; set phase=1 for new tasks."""
    phase = 1  # New tasks always start in phase 1
    insert = pg_insert(EmbeddingTask).values(
        candidate_id=candidate_id,
        model=self._model,
        locale=built.locale,
        text_hash=built.content_hash,
        phase=phase,  # NEW: set initial phase
        priority=embedding_priority(phase=phase),  # NEW: phase-aware priority
    )
    upsert = insert.on_conflict_do_update(
        index_elements=[EmbeddingTask.candidate_id, EmbeddingTask.model, EmbeddingTask.locale],
        index_where=OPEN_TASK_PREDICATE,
        set_={"text_hash": insert.excluded.text_hash, "updated_at": func.now()},
        # NOTE: phase is NOT updated on conflict; existing phase is preserved
        where=(EmbeddingTask.status == WorkTaskStatus.PENDING) & (EmbeddingTask.text_hash != built.content_hash),
    )
    return self._session.execute(upsert.returning(EmbeddingTask.id)).first() is not None
```

Also update the initial insert statement in enqueue:

```python
def enqueue(self, candidate_id: UUID, built: BuiltText) -> EnqueueOutcome:
    """Queue ``built`` for embedding unless its locale gets no vectors or the stored embedding has its hash."""
    if built.locale not in self._locales:
        return EnqueueOutcome.NOT_EMBEDDED
    if self._embedded_hash(candidate_id, built.locale) == built.content_hash:
        self._retire_pending(candidate_id, built.locale)
        return EnqueueOutcome.CURRENT
    queued = self._upsert_pending(candidate_id, built)
    return EnqueueOutcome.QUEUED if queued else EnqueueOutcome.LEFT_OPEN
```

Import `embedding_priority` and use it when calculating `priority` for new tasks.

**Refactor**: Check for duplication between priority calculation at insert vs. query time. Ensure all new task creation goes through `embedding_priority(phase=1)` to maintain consistency.

---

### Slice 4: Track Coverage Bitmap on Settlement

**Red**: Two tests:

1. **Happy path** — `test_settle_embedding_updates_coverage_bitmap`:
   - Setup: Candidate C with 10 locales; create pending embedding tasks for all locales, phase=1
   - Action: Claim and settle task for locale "en" (index 0)
   - Assert: `FairSelectionState(entity_id=C, pipeline='embedding').coverage_bitmap` has bit 0 set
   - Action: Settle task for locale "de" (index 1)
   - Assert: `coverage_bitmap` now has bits 0–1 set (0b0000011)

2. **Negative path** — `test_settle_embedding_does_not_update_on_failure`:
   - Setup: Same candidate C, 10 locales
   - Action: Claim task for locale "en", fail it (status=FAILED)
   - Assert: `coverage_bitmap` remains 0 (failure doesn't count as coverage)
   - Assert: Subsequent claims can still pick that locale (task can be retried)

**Green**: Update `app/features/search/task_settle.py` to track coverage:

```python
# In task_settle.py, in the settlement dispatch or complete handler:

from app.models.fair_selection import FairSelectionState

def _update_embedding_coverage_bitmap(session: Session, candidate_id: UUID, locale: str) -> None:
    """Record that candidate has an embedding in locale; update coverage bitmap."""
    from app.models.search import CANONICAL_LOCALE

    # Map locale to bit index (assume locales are sorted; use a registry if order changes)
    # For now: canonical locale = bit 0, others in sorted order
    locales = session.query(CandidateSearchText.locale).filter(
        CandidateSearchText.candidate_id == candidate_id
    ).order_by(CandidateSearchText.locale).all()
    locale_index = next((i for i, (loc,) in enumerate(locales) if loc == locale), 0)

    # Update or insert fair_selection_state with coverage bit set
    state = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == 'embedding',
        FairSelectionState.entity_id == candidate_id
    ).first()

    if state is None:
        state = FairSelectionState(
            pipeline='embedding',
            entity_id=candidate_id,
            phase=1,
            coverage_bitmap=1 << locale_index
        )
        session.add(state)
    else:
        state.coverage_bitmap |= (1 << locale_index)

    session.flush()
```

Call this function in the embedding task complete path (after `task_settle.complete_embedding_task()`).

Also add a query helper in `apps/api/app/features/search/repository.py`:

```python
def get_embedding_coverage_for_candidate(session: Session, candidate_id: UUID) -> int:
    """Get the coverage bitmap for a candidate's embeddings."""
    state = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == 'embedding',
        FairSelectionState.entity_id == candidate_id
    ).first()
    return state.coverage_bitmap if state else 0
```

**Refactor**: Check if coverage bitmap update logic is reused across pipelines (translation, discovery). If so, extract to a shared helper in `fair_selection.py` or similar; otherwise, keep inline here.

---

### Slice 5: Phase Transition Logic — Candidate → All Embeddings Complete

**Red**: Two tests:

1. **Happy path** — `test_embedding_phase_1_to_2_transition`:
   - Setup: 3 candidates (A, B, C), each with 10 locales, all phase=1; total 30 tasks
   - Action: Settle all 30 embedding tasks (all candidates, all locales complete)
   - Assert: Check transition logic (called from settlement or background job): all candidates now phase=2
   - Assert: Subsequent enqueue sets new tasks to phase=2 (or remains phase=1 if new entry)

2. **Negative path** — `test_embedding_phase_1_incomplete_no_transition`:
   - Setup: 3 candidates, 10 locales each; settle only 25 of 30 tasks (5 tasks remain)
   - Action: Check phase transition (all candidates, all locales)
   - Assert: Phase remains 1 (not all candidates have full coverage)
   - Assert: Next enqueue for incomplete locale still uses phase=1

**Green**: Add transition checker to `apps/api/app/features/search/phase.py`:

```python
def should_transition_embedding_phase_1_to_2(session: Session) -> bool:
    """Check if all candidates have embeddings in all locales (phase 1 → 2 trigger)."""
    from sqlalchemy import func, and_

    # Count total candidates with embeddings
    total_candidates = session.query(func.count(func.distinct(CandidateSearchText.candidate_id))).scalar() or 0

    if total_candidates == 0:
        return False

    # Count candidates with *complete* coverage (all locales embedded)
    # A candidate is "complete" if its coverage_bitmap matches the full mask for its locale count
    num_locales = session.query(func.count()).select_from(
        session.query(CandidateSearchText.locale).distinct()
    ).scalar() or 0

    if num_locales == 0:
        return False

    full_mask = (1 << num_locales) - 1

    complete_count = session.query(func.count(func.distinct(FairSelectionState.entity_id))).filter(
        FairSelectionState.pipeline == 'embedding',
        FairSelectionState.phase == 1,
        FairSelectionState.coverage_bitmap == full_mask,
    ).scalar() or 0

    # Phase 1 → 2 when ALL candidates have full coverage
    return complete_count >= total_candidates


def apply_embedding_phase_transition(session: Session) -> int:
    """Advance all phase-1 embeddings to phase 2 if conditions met; return count updated."""
    if not should_transition_embedding_phase_1_to_2(session):
        return 0

    from sqlalchemy import update

    result = session.execute(
        update(FairSelectionState).where(
            FairSelectionState.pipeline == 'embedding',
            FairSelectionState.phase == 1
        ).values(phase=2)
    )

    # Also update all pending/claimed tasks in phase 1 to reflect new phase
    # (optional: batch update task priorities; depends on settlement flow)
    return result.rowcount
```

Call `apply_embedding_phase_transition()` from the settlement dispatch (after embedding task completes) or from a background job. This is coordinated with C3 (state transition logic).

**Refactor**: Check if phase transition logic is similar across pipelines (translation, discovery). If patterns match, extract common helper; otherwise, keep pipeline-specific. Also ensure the full-mask calculation handles edge cases (new locales added after phase 1 started).

---

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Read phase | `test_get_phase_for_embedding_candidate_found` | `test_get_phase_for_embedding_candidate_missing` |
| Phase priority | `test_embedding_phase_affects_priority` | `test_embedding_uniform_within_phase` |
| Enqueue sets phase | `test_enqueue_embedding_sets_phase_1` | `test_enqueue_embedding_does_not_override_existing_phase` |
| Coverage bitmap | `test_settle_embedding_updates_coverage_bitmap` | `test_settle_embedding_does_not_update_on_failure` |
| Phase transition | `test_embedding_phase_1_to_2_transition` | `test_embedding_phase_1_incomplete_no_transition` |

## Review gate

Before merging:

1. All 10 tests (happy + negative for each slice) pass locally.
2. No N+1 queries: `get_phase_for_embedding()` and coverage bitmap queries are efficient (indexed on `pipeline`, `entity_id`).
3. Priority ordering verified: phase 1 tasks claim before phase 2 (via local queue test).
4. Coverage bitmap persisted correctly: post-settle query confirms bits set.
5. Phase transition only triggers when all candidates are complete (verify in test).
6. Backward compatibility: existing code (leased_queue, complete handler) works unchanged.
7. Code review: Check alignment with C4–C5 patterns (especially priority formula and phase-band calculation).
8. Docstrings: All new functions have docstrings (ruff D checks pass).

## Out of scope

- **State transition dispatch** (C3): C6 provides the transition checker; C3 wires it into the settlement loop
- **Leased queue phase field support** (C8): C8 adds phase_field parameter to claim; C6 assumes flat priority within phase
- **Settlement dispatch** (C9): C9 routes embedding settlements; C6 assumes callback is registered

## Verification

```bash
# Run from the repository root.
pytest tests/features/search/test_embedding_phase.py -v
pytest tests/features/search/ -k embedding -v
scripts/ci.sh lint  # Ensure docstrings pass ruff D rules
```

Expected:
- All 10 tests pass (5 slices × 2 tests each)
- Coverage bitmap queries run in < 10ms (single index lookup)
- Phase priority values in correct bands (0–99,999 and 100,000–199,999)
- No task starvation: phase 1 candidates claim 100% before phase 2 candidates see any work

## Refactor report

_Extracted `_phase_band(phase: int) -> int` helper from priority calculations (Slice 2). Used consistently across `first_priority()`, `retranslation_priority()`, and `embedding_priority()`. No other refactoring needed: each function has one concern (phase band + base offset), coverage bitmap update is isolated (Slice 4), transition logic is a single decision point (Slice 5). All within containing methods._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`. Pull it only when it tracks an upstream.
- Create the chapter branch with `git checkout -b c6-embedding-phase`.
- Commit the red tests first (10 tests, all failing), then the green changes (Slices 1–5), then refactoring.
- Run the local gate on the chapter branch: `pytest tests/features/search/test_embedding_phase.py && scripts/ci.sh lint` exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
