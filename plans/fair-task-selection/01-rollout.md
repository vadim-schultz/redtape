# Fair Task Selection - Implementation Rollout

## Overview

Eight implementation chapters across four phases. Critical path: 2 weeks (database schema → state management → pipeline integration → testing).

## Chapter Schedule Matrix

| ID | Title | Depends On | Touches | Owner | Gate | Status |
|----|----|----|----|----|----|---|
| C1 | Design phase-state machine & priority formula | — | docs | chapter-implementer | design review + unit tests | — |
| C2 | Create `fair_selection_state` table & migration | — | schema | chief-of-staff | migration runs successfully | — |
| C3 | Implement state transition logic | C2 | state module | chapter-implementer | unit tests (phase transitions) | — |
| C4 | Update translation priority (candidates) | C1 | `translation/priority.py` | chapter-implementer | unit + integration tests | — |
| C5 | Update translation priority (snapshots) | C1 | `translation/snapshot_enqueue.py` | chapter-implementer | unit + integration tests | — |
| C6 | Update embedding priority & phase tracking | C1 | `search/enqueue.py` | chapter-implementer | unit tests | — |
| C7 | Update discovery task selection | C1 | `discovery/repository/tasks.py` | chapter-implementer | unit tests (page-completeness + phase) | — |
| C8 | Modify `LeasedQueue.claim()` for phase/grouping | C2, C3 | `search/leased_queue.py` | chapter-implementer | unit tests (order verification) | — |
| C9 | Add observability & metrics | C3–C8 | metrics module | chapter-implementer | metrics emit correctly | — |
| C10 | End-to-end integration & validation | C3–C9 | test suite | chapter-implementer | 3 integration tests pass | — |

## Parallel Batches

### Batch 1 (Design & Schema)
**Chapters**: C1, C2
**Why parallel**: C1 is design docs (no code dependencies); C2 is schema-only (no business logic yet)
**Duration**: ~2 days

### Batch 2 (State Management & Pipeline Priorities)
**Chapters**: C3, C4, C5, C6, C7
**Why parallel**: Each depends on C1 (design) and C2 (schema) but not on each other (each pipeline is independent)
**Duration**: ~5 days
**Integration**: Chapters touch different files; no conflicts

### Batch 3 (Queue Integration)
**Chapters**: C8
**Why serial after Batch 2**: C8 integrates all pipeline priorities via `LeasedQueue.claim()` changes; must come after individual pipelines are updated
**Duration**: ~2 days

### Batch 4 (Observability & Testing)
**Chapters**: C9, C10
**Why serial after Batch 3**: C9 adds metrics that C10 tests; C10 is final validation
**Duration**: ~3 days

## Integration Order

Each chapter integrates into the loop branch locally (`git merge --no-ff`) in dependency order:

1. C1 → C2 (design feeds schema)
2. C2 → C3 (schema enables state logic)
3. C3 → {C4, C5, C6, C7} (state logic enables pipeline updates; integrate in any order)
4. C4, C5, C6, C7 → C8 (all pipelines updated before queue integration)
5. C8 → C9 (queue logic before metrics)
6. C9 → C10 (metrics before validation)

## Critical Path

**Longest dependency chain**:
```
C1 (2 days) → C2 (2 days) → C3 (1 day) → {C4–C7 in parallel, 5 days}
  → C8 (2 days) → C9 (1 day) → C10 (3 days)
Total: ~16 days
```

**Compression opportunities**:
- C9 metrics can be drafted in parallel with C8 (no code dependency)
- C10 test suite can be drafted in parallel with C8–C9 (depends on completed pipelines)

## Per-Chapter Gate

Each chapter:
1. ✅ Runs `scripts/ci.sh lint` locally (ruff, mypy, format)
2. ✅ Runs unit tests for affected modules (`pytest apps/api/tests/<module>`)
3. ✅ Passes TDD red → green → refactor loop (paired tests for each slice)
4. ✅ Reports: paired test names, refactor outcome, narrow & full gate results

**Full suite before release**:
- `pytest` (all tests)
- `ruff check`, `ruff format --check`
- Deployment dry-run

## Risks & Contingencies

| Risk | Probability | Impact | Mitigation |
|------|----|----|---|
| Phase transition logic has off-by-one error | Medium | Stalls work (need fix) | C10 integration tests catch this; manual override in C3 during C10 |
| Priority formula breaks compatibility | Low | Old tasks stuck | Backfill migration in C2; C8 handles gracefully |
| State table grows too large | Low | Query slowdown | Add index on (entity_id, pipeline); partition if >1M rows |
| Coverage tracking drifts | Medium | Stalls phase 1→2 transition | C3 includes periodic audit; C9 metrics expose drift |

## Local Gate Command

For each chapter:
```bash
./scripts/ci.sh
```

Before release (all chapters integrated):
```bash
pytest
ruff check apps/api apps/discovery-ingest
ruff format --check apps/api apps/discovery-ingest
```

## Deliverables

1. **C1 output**: `plans/fair-task-selection/00-architecture.md` (this document) + design doc in C1 chapter
2. **C2 output**: Migration file (e.g., `001_create_fair_selection_state.sql`)
3. **C3–C9 output**: Module code, unit tests, metrics
4. **C10 output**: Integration test suite (3+ end-to-end tests)
5. **Final**: Updated `01-rollout.md` with actual timings; merge to main via release PR
