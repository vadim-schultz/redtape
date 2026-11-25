# Fair Task Selection Strategy - Architecture

**Design reviewed and validated in C1.** See [`docs/FAIR_SELECTION_DESIGN.md`](../../docs/FAIR_SELECTION_DESIGN.md) and [`docs/FAIR_SELECTION_STATE_DIAGRAM.txt`](../../docs/FAIR_SELECTION_STATE_DIAGRAM.txt) for detailed design documentation and state diagram.

## Overview

Redtape processes documents through five pipelines: **Discovery** (crawl, render, extract), **Translation** (candidates and pages), **Embedding** (search vectors), and **Screenshots** (UI capture). Each pipeline uses a leased work-queue with priority-based selection.

**Problem**: Translation and Embedding pipelines rank work by **confidence** (high-confidence candidates get repeated work while low-confidence candidates never get touched). Discovery has a partial mitigation (page completeness tie-break), but it's not unified across all pipelines.

**Root cause**: Within each priority band, tasks are sorted by `created_at ASC`, so old high-confidence tasks block new low-confidence tasks indefinitely.

## Solution: Three-Phase Selection Strategy

### Phase 1: Breadth-First Coverage
**Goal**: Every document gets at least one task of each type completed.

**Mechanism**:
1. Track per-document **phase state**: phase 1 incomplete (needs coverage), phase 2 (can deepen), phase 3 (refresh mode)
2. Modify priority calculation: add a **phase component** so phase-1-incomplete items always outrank phase-2 items
3. Within phase 1, use **grouping by document** so all locales of one document are claimed together before moving to the next

**Example**:
- Document A (high confidence, 100 tasks): Claims 10 locales, moves to phase 2
- Document B (low confidence, 100 tasks): Claims 10 locales, moves to phase 2
- Repeat until all documents phase 2

### Phase 2: Depth-First Completion
**Goal**: Complete remaining work on partially-done documents.

**Mechanism**:
1. When all documents have at least one translation per locale (or per pipeline requirement), mark phase transition
2. Revert to confidence-based selection (high-quality items now prioritized)
3. Continue with normal prioritization until all items complete

### Phase 3: Refresh Mode
**Goal**: Re-enqueue work when source data changes.

**Mechanism**:
1. If source or candidate changes, re-enqueue as phase 3
2. Phase 3 items rank below phase 1 and 2
3. When all phase 1–2 work done, process phase 3

## Data Model

### New Table: `fair_selection_state`
```sql
CREATE TABLE fair_selection_state (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  pipeline TEXT NOT NULL, -- 'translation', 'embedding', 'discovery'
  entity_id UUID NOT NULL, -- candidate_id or catalogue_service_id
  phase INTEGER DEFAULT 1, -- 1 = breadth-first, 2 = depth-first, 3 = refresh
  coverage_bitmap BIGINT DEFAULT 0, -- bitmask of completed task types
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE (pipeline, entity_id)
);

CREATE INDEX ix_fair_selection_state_pipeline_entity
  ON fair_selection_state(pipeline, entity_id);
```

### Modified: Task Tables
Add optional `phase` column (defaults to 1 for new tasks):
- `translation_task.phase`
- `snapshot_translation_task.phase`
- `embedding_task.phase`
- `discovery_task.phase`

## Priority Formula

**New formula** (unified across pipelines):

```
priority = (phase_component * 100_000) + (confidence_rank * 100) + locale_index

Where:
  phase_component = 0 if phase 1, 1 if phase 2, 2 if phase 3
  confidence_rank = 0–1000 (higher = lower priority, as before)
  locale_index = 0–99 (stable tie-break within (phase, rank))
```

**Result**:
- Phase 1 tasks: 0–99,999 (always claim before phase 2)
- Phase 2 tasks: 100,000–199,999 (always claim before phase 3)
- Phase 3 tasks: 200,000+ (refresh, claim last)

Within phase 1, tasks of the same locale_index are grouped by document (via grouping parameter in claim).

## Pipeline Integration

### Translation (Candidates)
- File: `apps/api/app/features/translation/priority.py`
- Change: `snapshot_first_priority()` and `snapshot_retranslation_priority()` now read phase from `fair_selection_state` and add phase component
- Grouping: Claim groups by `candidate_id` to keep all locales of one candidate together

### Translation (Snapshots)
- File: `apps/api/app/features/translation/snapshot_enqueue.py`
- Change: Same phase-aware priority as candidates
- Grouping: Claim groups by `catalogue_service_id` to keep all locales of one page together

### Embedding
- File: `apps/api/app/features/search/enqueue.py`
- Change: Set initial phase = 1 for new tasks; phase transitions when embedding is complete for a candidate
- Priority: Uniform (always 100 within pipeline), but phase component added

### Discovery
- File: `apps/api/app/features/discovery/repository/tasks.py`
- Change: Extend page-completeness boost to also consider global phase state
- Priority: Use page-completeness as secondary ordering (existing D7 decision), add phase component

## Claim & Selection Logic

### Modified: `LeasedQueue.claim()` (generic base class)
- Accept `grouping_field` and `phase_field` parameters
- Order: `phase ASC, priority ASC, grouping ASC, created_at ASC, id ASC`
- Respect phase tie-breaks: group all work for one (phase, priority) before moving to next

### Worker Integration
- Discovery ingest worker already handles claim; no changes needed there
- Drain loops remain unchanged; queues enforce order

## State Transitions

### Auto-Transition Rules

**Phase 1 → Phase 2**:
- Triggered when: All documents in catalogue have at least one **completed** task per pipeline-locale combination
- Action: Update `fair_selection_state.phase = 2` for all entities; re-calculate priorities
- Cadence: Check on each settlement (after claim completes)

**Phase 2 → Phase 3** (or loop):
- Triggered when: All phase 2 tasks are COMPLETED
- Action: If any phase 3 items exist, set phase = 3; else return to phase 1 for a new cycle (optional: or stop)

### Manual Override
- Admin can force a document into phase 2 (expedite) or phase 3 (refresh) if needed

## Observability & Metrics

Add counters:
- `task_queue_pending_by_phase` — per pipeline, per phase
- `task_queue_claimed_by_phase` — per pipeline, per phase
- `fair_selection_phase_transition` — log when phase changes
- `document_coverage_pct` — % of documents with ≥1 complete task per locale

## Success Criteria

- ✅ All documents get ≥1 task per locale attempted within defined time window
- ✅ No task starves for >7 days (auto-promote if needed)
- ✅ Phase transitions happen automatically; no manual intervention
- ✅ Coverage increases monotonically in phase 1 (no regression)
- ✅ Existing confidence-based prioritization preserved in phase 2
- ✅ Metrics show clear phase boundaries and transitions

## Assumptions

1. **Throughput**: ~100 tasks/hour per worker. Phase 1 for 4000 candidates × 10 locales (40,000 tasks) completes in ~400 hours (~17 days).
2. **Locales fixed**: ≤64 locales across all pipelines. If more added, switch bitmap to BYTEA.
3. **No cascading deletes**: Candidates not soft-deleted; if deleted, manually clean `fair_selection_state`.
4. **Enqueue is idempotent**: Calling `enqueue_many()` twice with same parameters is safe (uses upsert).
5. **Workers respect priority**: Task claim logic orders by priority; workers claim highest-priority tasks first.
