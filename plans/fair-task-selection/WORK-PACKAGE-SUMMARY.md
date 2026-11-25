# Fair Task Selection - Work Package Summary

## What Was Created

A complete work package for implementing fair task selection across all five redtape pipelines (Discovery, Translation, Embedding, Screenshots). The package includes 10 implementation chapters, design documents, and execution framework.

## Files Generated

```
/mnt/projects/redtape/plans/fair-task-selection/
├── 00-architecture.md                    # Design overview
├── 01-rollout.md                         # Execution schedule (now outdated; use chapters/)
├── chapters/
│   ├── README.md                         # Chapter overview & patterns
│   ├── c1-design-phase-state.md          # Design phase-state machine
│   ├── c2-schema-migration.md            # Create fair_selection_state table
│   ├── c3-state-transitions.md           # Implement auto phase transitions
│   ├── c4-translation-priority.md        # Update translation (candidates) priority
│   ├── c5-snapshot-priority.md           # Update translation (snapshots) priority
│   ├── c6-embedding-phase.md             # Update embedding priority
│   ├── c7-discovery-phase.md             # Update discovery task selection
│   ├── c8-leased-queue-integration.md    # Integrate queue ordering
│   ├── c9-metrics-observability.md       # Add observability & metrics
│   └── c10-integration-validation.md     # End-to-end validation
├── gaps-and-decisions.md                 # Open questions & design decisions
├── run-ledger.md                         # Execution log template
└── WORK-PACKAGE-SUMMARY.md              # This file
```

## Execution Model

**Chief-of-Staff Orchestration**:
1. Schedules chapters in dependency-aware batches
2. Launches `chapter-implementer` agents in parallel (independent worktrees)
3. Each agent runs local gate (`scripts/ci.sh`)
4. Chief merges chapters into loop branch locally (no remote push)
5. After all chapters: creates release PR to main

**Batches**:
- **Batch 1** (Days 1–2): C1 (design), C2 (schema)
- **Batch 2** (Days 3–7): C3–C7 (state management + pipeline priorities, all parallel)
- **Batch 3** (Days 8–9): C8 (queue integration)
- **Batch 4** (Days 10–13): C9–C10 (metrics + validation)

**Critical Path**: ~16 days (C1 → C2 → C3 → {C4–C7} → C8 → C9 → C10)

## What Each Chapter Does

### C1: Design (Design-only)
- State machine diagram (phase 1 → 2 → 3 transitions)
- Priority formula proof (phase bands prevent starvation)
- Coverage bitmap design (64-bit BIGINT per document)
- Performance estimates (40,000 tasks ÷ 100/hr = 17 days per cycle)
- Release notes draft

### C2: Schema (SQL + ORM)
- Create `fair_selection_state` table with indices
- Add `phase` column to 4 task tables (defaults to 1)
- Write migration script (idempotent, with backfill)
- Update SQLAlchemy ORM models

### C3: State Management (Python module)
- Implement `check_phase_one_complete()` (coverage checker)
- Implement `transition_phase()` (state machine)
- Implement `audit_fair_selection_state()` (drift detection)
- Hook into task settlement to auto-trigger transitions
- Add Prometheus metrics for transitions

### C4–C7: Pipeline Priorities (Python + SQL)
Each updates one pipeline's priority formula:
- **C4**: Translation (candidates) — read phase, add phase band to priority
- **C5**: Translation (snapshots) — same formula, group by page not candidate
- **C6**: Embedding — uniform priority + phase band (always 100 within pipeline)
- **C7**: Discovery — extend page completeness to include phase

All follow same pattern: batch-read phase, modify priority formula, test with phase bands.

### C8: Queue Integration (Python base class)
- Modify `LeasedQueue.claim()` to accept `phase_field` and `grouping_field`
- Update SQL order-by: `phase ASC, priority ASC, grouping ASC, created_at ASC, id ASC`
- Extract `claim_tasks_with_grouping()` factory
- Update all 4 pipelines to pass grouping field (candidate_id or catalogue_service_id)

### C9: Observability (Prometheus metrics)
- `task_queue_pending_by_phase` — per pipeline, per phase
- `task_queue_claimed_by_phase` — per pipeline, per phase
- `fair_selection_phase_transition` — log phase changes with count
- `document_coverage_pct` — % of documents with ≥1 completed task

### C10: Validation (Integration tests)
- **Test 1**: Breadth-first ordering (all documents touched before repeating)
- **Test 2**: Phase transitions (auto-trigger when phase-1 complete)
- **Test 3**: Coverage tracking (bitmap audit catches drifts)
- **Test 4**: Stress test (1000 concurrent claims without deadlock)
- **Test 5**: Rollback resilience (old code doesn't crash)

## Success Criteria

✅ All documents get ≥1 task per locale attempted within defined time window
✅ No task starves for >7 days (auto-promote if needed)
✅ Phase transitions happen automatically
✅ Coverage increases monotonically in phase 1
✅ Existing confidence-based prioritization preserved in phase 2
✅ Metrics show clear phase boundaries and transitions

## How to Execute

1. **Create work package**: (Already done by work-package-create skill)

2. **Execute with chief-of-staff**:
   ```bash
   /chief-of-staff @plans/fair-task-selection
   ```

3. **Chief-of-staff will**:
   - Verify all chapters pass local gates
   - Schedule Batch 1 (C1, C2 parallel)
   - After Batch 1 integrates: schedule Batch 2 (C3–C7 parallel)
   - After Batch 2 integrates: schedule Batch 3 (C8)
   - After Batch 3 integrates: schedule Batch 4 (C9–C10)
   - After all chapters integrate: create release PR to main

4. **Each chapter-implementer agent**:
   - Branches from loop branch (`feat/plans-pipeline-optimisation`)
   - Implements 5 TDD slices (red → green → refactor)
   - Runs local gate (`scripts/ci.sh`)
   - Reports: paired tests, refactor outcome, gate result
   - Returns to chief-of-staff for integration

## Key Design Decisions

1. **Phase-band priority** (`(phase - 1) * 100_000`) ensures phase 1 items (0–99,999) always rank before phase 2 (100,000–199,999) without overlap. Prevents starvation.

2. **Document grouping** (by candidate_id or catalogue_service_id) ensures all 10 locales of one document claim together before moving to next. Fair coverage per document.

3. **Automatic transitions** (checked on each settlement) mean no manual intervention. Phase advances when trigger conditions met.

4. **Coverage bitmap** (BIGINT, 64 bits) supports 10 current locales with 6× headroom. Tracks only COMPLETED tasks (not CLAIMED-but-incomplete).

5. **Shared state table** (`fair_selection_state`) unifies phase tracking across all pipelines (translation, embedding, discovery). Single source of truth.

## Known Flags (from Phase B Review)

⚠️ **Flag 2**: C3 & C8 integration points unclear — added explicit filename references in chapters
⚠️ **Flag 5**: C9 pipeline mapping repeated twice — recommend extracting to constant before merging
⚠️ **Flag 6**: C10 stress test needs thread-safe session factory — documented in C10
⚠️ **Flag 7**: C10 coverage bitmap test assumes locale ordering — add helper to query actual DB order

(All flags are quality observations, not blockers.)

## Next Steps

1. Review this summary and the architecture document
2. Run `/chief-of-staff @plans/fair-task-selection` to begin execution
3. Monitor run-ledger.md as chapters integrate
4. After all chapters complete, release to main via release PR

## References

- **Architecture**: `00-architecture.md` (design overview, data model, priority formula)
- **Schedule**: `01-rollout.md` (parallel batches, critical path, per-chapter gate)
- **Gaps & Decisions**: `gaps-and-decisions.md` (5 open Qs, 4 design decisions, 5 risks)
- **Chapters**: `chapters/` directory (10 implementation chapters, each with 5 TDD slices)
- **Ledger**: `run-ledger.md` (execution log, timings, risks)
