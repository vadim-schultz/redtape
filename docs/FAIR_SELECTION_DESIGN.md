# Fair Task Selection Strategy - Design

## Problem Statement

Redtape processes documents through five pipelines: **Discovery** (crawl, render, extract), **Translation** (candidates and pages), **Embedding** (search vectors), and **Screenshots** (UI capture). Each pipeline uses a leased work-queue with priority-based selection.

**The challenge**: Translation and Embedding pipelines rank work by **confidence** (high-confidence candidates get repeated work while low-confidence candidates never get touched). This creates starvation: a low-confidence document may never be processed if high-confidence documents keep accumulating work.

**Root cause**: Within each priority band, tasks are sorted by `created_at ASC`, so old high-confidence tasks block new low-confidence tasks indefinitely.

## Solution: Three-Phase Selection Strategy

### Phase 1: Breadth-First Coverage

**Goal**: Every document gets at least one task of each type completed.

**How it works**:
1. When a new batch of documents enters the system, they are marked as **phase 1 (breadth-first)**.
2. Within phase 1, task selection ignores confidence and focuses on **covering all documents at least once per locale**.
3. When a document has ≥1 completed task per locale, it moves to **phase 2 (depth-first)**.
4. Phase 1 → Phase 2 transition happens automatically when **all documents in the system have ≥1 completed task per locale**.

**Example**:
- Document A (high confidence, 100 tasks): Claims 10 locales, marks phase 2
- Document B (low confidence, 100 tasks): Claims 10 locales, marks phase 2
- Repeat until all documents phase 2

**Duration**: For 4000 candidates × 10 locales (40,000 tasks) at ~100 tasks/hour throughput = ~17 days.

### Phase 2: Depth-First Completion

**Goal**: Complete remaining work on partially-done documents.

**How it works**:
1. When all documents have at least one translation per locale, the system marks **phase transition**.
2. Revert to confidence-based selection (high-quality items now prioritized).
3. Continue with normal prioritization until all items complete.

**Benefit**: Low-confidence documents get fair coverage even if they can never compete with high-confidence items in pure confidence ordering.

### Phase 3: Refresh Mode

**Goal**: Re-enqueue work when source data changes.

**How it works**:
1. If source or candidate changes, re-enqueue as phase 3.
2. Phase 3 items rank below phase 1 and 2.
3. When all phase 1–2 work done, process phase 3.

## Priority Formula

**Priority calculation** (unified across pipelines):

```
priority = (phase_component * 100_000) + (confidence_rank * 100) + locale_index

Where:
  phase_component = 0 if phase 1, 100_000 if phase 2, 200_000 if phase 3
  confidence_rank = 1000 - round(confidence * 1000)
    (higher confidence = lower rank, lower priority)
  locale_index = 0–99 (stable tie-break within (phase, rank))
```

**Result**:
- Phase 1 tasks: 0–99,999 (always claim before phase 2)
- Phase 2 tasks: 100,000–199,999 (always claim before phase 3)
- Phase 3 tasks: 200,000+ (refresh, claim last)

**Proof of no-starvation**:
Within phase 1, all items range 0–99,999; phase 2 items range 100,000+. It is **impossible** for phase 2 to invert the order. The barrier is maintained by the formula itself.

## Coverage Tracking

Track per-document **phase state** using a bitmap:

```sql
CREATE TABLE fair_selection_state (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  pipeline TEXT NOT NULL, -- 'translation', 'embedding', 'discovery'
  entity_id UUID NOT NULL, -- candidate_id or catalogue_service_id
  phase INTEGER DEFAULT 1, -- 1 = breadth-first, 2 = depth-first, 3 = refresh
  coverage_bitmap BIGINT DEFAULT 0, -- bitmask of completed locales (bits 0–63)
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE (pipeline, entity_id)
);

CREATE INDEX ix_fair_selection_state_pipeline_entity
  ON fair_selection_state(pipeline, entity_id);
```

**Algorithm**:
- On task settlement: `UPDATE fair_selection_state SET coverage_bitmap = coverage_bitmap | (1 << locale_index) WHERE entity_id = ? AND pipeline = ?`
- Phase 1 → 2 trigger: Count rows where `coverage_bitmap = (1 << num_locales) - 1` = 0 (all bits set for each document)
- Assumption: ≤64 locales (true for foreseeable future; can switch to BYTEA if needed)

## State Transitions

### Phase 1 → Phase 2

**Trigger**: All documents have at least one **completed** task per pipeline-locale combination.

**Action**: Update `fair_selection_state.phase = 2` for all entities; re-calculate priorities.

**Cadence**: Check on each task settlement (after claim completes).

### Phase 2 → Phase 3 (or loop)

**Trigger**: All phase 2 tasks are COMPLETED.

**Action**: If any phase 3 items exist, set phase = 3; else return to phase 1 for a new cycle (optional: or stop).

**Cadence**: Periodic check (hourly or on-demand).

## Performance Estimates

- **4000 candidates** × 10 locales = 40,000 tasks
- **Throughput**: ~100 tasks/hour (from observed worker drain rates)
- **Phase 1 duration**: ~400 hours = ~17 days
- **Acceptable**: Gives fair coverage within reasonable time

## Benefits

1. **Starvation prevention**: All documents get fair coverage before high-confidence prioritization resumes.
2. **Bounded wait time**: Low-confidence documents complete phase 1 coverage in ~17 days (predictable).
3. **Backward compatible**: Phase 2 preserves existing confidence-based prioritization.
4. **Automatic operation**: No manual intervention needed; phase transitions happen on task settlement.
5. **Observable**: Metrics expose phase distribution and transitions.

## Deployment Timeline

- C1: Design (2 days) ← You are here
- C2: Schema migration (2 days)
- C3: State transition logic (1 day)
- C4–C7: Pipeline integration (5 days parallel)
- C8: Queue integration (2 days)
- C9: Metrics & observability (1 day)
- C10: End-to-end validation (3 days)

**Total**: ~16 days

## Assumptions

1. **Throughput**: ~100 tasks/hour per worker. Phase 1 for 4000 candidates × 10 locales (40,000 tasks) completes in ~400 hours (~17 days).
2. **Locales fixed**: ≤64 locales across all pipelines. If more added, switch bitmap to BYTEA.
3. **No cascading deletes**: Candidates not soft-deleted; if deleted, manually clean `fair_selection_state`.
4. **Enqueue is idempotent**: Calling `enqueue_many()` twice with same parameters is safe (uses upsert).
5. **Workers respect priority**: Task claim logic orders by priority; workers claim highest-priority tasks first.

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|----|----|
| Phase transition logic has off-by-one error | Medium | C10 integration tests catch this; manual override in C3 during C10 |
| Priority formula breaks compatibility | Low | Backfill migration in C2; C8 handles gracefully |
| State table grows too large | Low | Add index on (entity_id, pipeline); partition if >1M rows |
| Coverage tracking drifts | Medium | C3 includes periodic audit; C9 metrics expose drift |

## Success Criteria

- ✅ All documents get ≥1 task per locale attempted within defined time window (~17 days)
- ✅ No task starves for >7 days (auto-promote if needed)
- ✅ Phase transitions happen automatically; no manual intervention
- ✅ Coverage increases monotonically in phase 1 (no regression)
- ✅ Existing confidence-based prioritization preserved in phase 2
- ✅ Metrics show clear phase boundaries and transitions
