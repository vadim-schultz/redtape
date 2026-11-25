# Fair Task Selection - Gaps, Decisions & Open Questions

## Open Questions

### Q1: Should phase transitions be automatic or admin-triggered?
**Current plan**: Automatic (check on each task settlement).
**Alternative**: Admin-triggered (operator runs migration when ready).
**Impact**: Automatic = simpler (less manual ops), but risky if transition logic has bug. Admin-triggered = safer but requires coordination.
**Decision**: Automatic, with override capability (admin can force phase=2 or reset phase=1 if needed).

### Q2: What happens to in-flight tasks when phase transitions?
**Scenario**: Candidate X is mid-translation (5 locales claimed, 5 pending). Phase 1 → 2 triggered.
**Current plan**: Existing tasks keep their priority; new enqueued tasks use phase 2.
**Alternative**: Recalculate all pending tasks to new priority (costly, risk of re-claim).
**Decision**: Keep existing task priorities (no recalc). They'll settle at phase-1 priority, then future enqueues of that candidate use phase 2.

### Q3: Timeout for phase 1 → 2 auto-transition?
**Current plan**: None (wait for all documents to have ≥1 complete task).
**Alternative**: Auto-promote to phase 2 after N days (e.g., 30 days) even if not all documents covered.
**Impact**: Prevents indefinite phase-1 stalling if coverage is slow.
**Decision**: Add optional timeout config (default: disabled). If stalling is observed, enable timeout.

### Q4: Coverage bitmap — when does it get reset?
**Scenario**: Document X is in phase 2 (bitmap=0b1111111111, all 10 locales done). Source updates; re-enqueue as phase 3.
**Current plan**: Bitmap doesn't reset; remains at "all complete". On phase 3 → 1 cycle, reset to 0.
**Alternative**: Reset bitmap whenever phase changes.
**Decision**: Keep bitmap for phase 1 & 2; reset when entering phase 1 again (refresh cycle).

### Q5: Should discovery pipeline participate in phase selection?
**Current plan**: Yes (C7 adds phase component to discovery tasks).
**Alternative**: Only translation/embedding use phases; discovery stays confidence-based.
**Impact**: Yes = unified fair coverage; No = discovery stays simple, but high-confidence URLs get crawled repeatedly.
**Decision**: Yes, include discovery. Use same phase state table but different entity_id (catalogue_service_id for discovery, candidate_id for translation/embedding).

## Design Decisions

### D1: Why coverage bitmap instead of explicit table of completed locales?
**Rationale**:
- Bitmap is compact (1 BIGINT vs. 10 rows per document)
- Fast query: `WHERE coverage_bitmap = (1 << num_locales) - 1`
- Assumption: ≤64 locales (true for foreseeable future; can switch to BYTEA if needed)

### D2: Why phase-band priority instead of separate queue?
**Rationale**:
- Single queue simplifies worker drain logic (no need to pick which queue to claim from)
- Phase is just a priority modifier; existing claim logic works unchanged
- Backports to discovery easily (phase-completeness is already a secondary tie-break)

### D3: Why group by entity (candidate/page) instead of by locale?
**Rationale**:
- Locale grouping would claim [en, de, fr] for 3 different candidates, spreading work
- Entity grouping claims [en, de, fr] for one candidate, then moves to next candidate
- Entity grouping is fairer: candidate A gets all 3 locales before candidate B starts
- Existing snapshot translation already groups by catalogue_service_id; just extending pattern

### D4: Why upsert pending tasks instead of delete + create?
**Rationale**:
- Atomic: no race condition if task settles between delete and create
- Preserves task.id (external systems may reference it)
- Idempotent: re-enqueuing same (candidate, locale) is safe

## Risks & Mitigations

### Risk 1: Phase transition logic has off-by-one error
**Scenario**: Phase 1 → 2 never triggers, work stalls.
**Mitigation**:
- C10 integration tests explicitly check phase transition
- Admin override: `UPDATE fair_selection_state SET phase=2 WHERE pipeline='translation'` (manual escape hatch)
- Metrics alert if phase doesn't transition within expected time

### Risk 2: Coverage bitmap drifts (doesn't match actual completion)
**Scenario**: Task settles but bitmap doesn't update; document appears phase-2-ready but isn't.
**Mitigation**:
- C3 includes periodic audit job (`audit_coverage_state()`) that recomputes bitmap from completed tasks
- Audit runs hourly or on-demand
- Alerts if discrepancy found

### Risk 3: New candidates enqueued during phase 1 get stuck at phase 2
**Scenario**: Phase 1 → 2 triggered at day 15. New candidate enqueued at day 16; inserted with phase=1 (default). But all other candidates already have phase=2 tasks claiming ahead.
**Mitigation**:
- Enqueue logic always reads current phase from database (no hardcoded defaults)
- New candidates inserted with phase=1; they'll be claimed in breadth-first order behind phase-1 tail
- Acceptable: new candidates inherit the system's current phase

### Risk 4: Performance hit from reading phase per enqueue batch
**Scenario**: Enqueue 1000 candidates; query `fair_selection_state` 1000 times (N+1).
**Mitigation**:
- Batch query: `get_phases_for_candidates([...])` fetches all in one query
- Cache result if same batch called multiple times
- Monitor query performance; index on (pipeline, entity_id)

### Risk 5: Locale index collides between documents
**Scenario**: Document A locale 0 priority = 100, Document B locale 0 priority = 100. Queue claim picks randomly.
**Mitigation**:
- Locale index is only for stability within same (phase, candidate, rank)
- Different documents have different entity_ids; claim groups by entity_id
- No collision; they're in separate groups

## Assumptions

1. **Throughput**: ~100 tasks/hour per worker. Phase 1 for 4000 candidates × 10 locales (40,000 tasks) completes in ~400 hours (~17 days).
2. **Locales fixed**: ≤64 locales across all pipelines. If more added, switch bitmap to BYTEA.
3. **No cascading deletes**: Candidates not soft-deleted; if deleted, manually clean `fair_selection_state`.
4. **Enqueue is idempotent**: Calling `enqueue_many()` twice with same parameters is safe (uses upsert).
5. **Workers respect priority**: Task claim logic orders by priority; workers claim highest-priority tasks first.

## Future Enhancements (Out of Scope)

1. **Weighted phases**: Instead of strict phase order, weight phases (e.g., 70% phase-1, 30% phase-2). Requires priority formula change.
2. **Per-locale phase tracking**: Track phase per (candidate, locale) instead of per candidate. More granular but higher cardinality.
3. **Priority starvation detection**: Auto-promote tasks that haven't been claimed in >N days to phase 0 (super-high priority).
4. **Dynamic locale lists**: Support adding/removing locales mid-cycle without recompiling bitmap.
5. **Multi-worker coordination**: Dedicated worker per phase (phase-1 worker, phase-2 worker) to ensure fairness. Requires worker pool management.

## Implementation Order Rationale

**Why C1 before C2?**
Design doc + formula derivation before schema; design may reveal schema requirements.

**Why C2 before C3?**
Schema must exist before state-transition logic runs queries.

**Why C3 before {C4–C7}?**
State transitions are shared; pipelines depend on them.

**Why {C4–C7} parallel, then C8?**
Each pipeline is independent; C8 integrates all via queue.

**Why C8 before C9?**
Metrics need queue integration to be meaningful.

**Why C9 before C10?**
Integration tests depend on metrics for observability.

## Rollback Plan

If issues emerge post-deployment:

1. **Revert code**: `git revert` release commit (all chapters)
2. **Keep schema**: Leave `fair_selection_state` table in place (no data loss)
3. **Disable phase logic**: Set all `phase` columns to 1; enqueue always uses `first_priority(confidence, phase=1)` (effectively ignores phase)
4. **Manual cleanup**: If needed, truncate `fair_selection_state`

Downtime: ~15 mins (redeploy code, verify queue health).

## Validation Checklist (Pre-Release)

- [ ] All chapters pass local CI (C1–C10 each run `pytest` + `scripts/ci.sh`)
- [ ] Integration test: 3 candidates (1 high, 1 low, 1 high), 3 locales each; verify breadth-first claim order
- [ ] Phase transition test: Enqueue 100 tasks, settle all, verify auto-transition to phase 2
- [ ] Coverage bitmap test: Verify bitmap tracks completed tasks correctly
- [ ] Rollback test: Revert code, verify queue still functional (phase=1, no errors)
- [ ] Load test: 1000 tasks claimed concurrently; verify no deadlocks or race conditions
- [ ] Metrics test: Verify `task_queue_pending_by_phase` emits correct values
