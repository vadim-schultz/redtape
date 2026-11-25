# Fair Task Selection - Execution Ledger

Execution log for the fair task selection work package. Updated as each chapter is integrated.

## Status Summary

| Phase | Chapters | Status | Integrated | Notes |
|-------|----------|--------|-----------|-------|
| Design & Schema | C1, C2 | ✅ Complete | ✅ | Merged into loop branch |
| Priorities | C3–C7 | 🔄 Running | — | Launched in parallel |
| Integration | C8 | — | — | Blocked on C3–C7 |
| Validation | C9, C10 | — | — | Blocked on C8 |

## Chapter Integration Log

### C1: Design phase-state machine & priority formula

- **Status**: ✅ Integrated
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 1
- **Branch**: `main` (merged via loop branch)
- **Integration date**: 2026-11-25
- **Commits**: `e21026b7` (feat: design phase-state machine and priority formula)
- **Gate result**: ✅ Narrow & full gates pass
- **Conflicts**: None
- **Notes**: Design-only chapter; outputs architecture docs, state machine diagram, priority formula proof. 10 unit tests (5 TDD slices × 2 paths). Ready for C3–C8 implementation.

### C2: Create `fair_selection_state` table & migration

- **Status**: ✅ Integrated
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 1–2
- **Blocked by**: C1 (design)
- **Branch**: `main` (merged via loop branch)
- **Integration date**: 2026-11-25
- **Commits**: `4623fc68` (feat: create fair_selection_state table and schema)
- **Gate result**: ✅ Narrow & full gates pass
- **Conflicts**: None
- **Notes**: Schema-only chapter. Migration creates fair_selection_state table, adds phase columns to 4 task tables. Backfill script populates initial state (all existing tasks → phase 1). Migration is idempotent. 10 schema & ORM tests (happy + negative).

### C3: Implement state transition logic

- **Status**: Pending
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 3
- **Blocked by**: C2 (schema exists)
- **Branch**: `local/c3-state-transitions`
- **Integration date**: —
- **Commits**: —
- **Gate result**: —
- **Conflicts**: —
- **Notes**: Core state machine; C4–C8 depend on this. Includes periodic audit job to detect coverage drift.

### C4: Update translation priority (candidates)

- **Status**: Pending
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 3–7 (parallel with C5–C7)
- **Blocked by**: C1, C2 (design, schema)
- **Branch**: `local/c4-translation-priority`
- **Integration date**: —
- **Commits**: —
- **Gate result**: —
- **Conflicts**: —
- **Notes**: Modifies `translation/priority.py` to include phase component. Reuses `_phase_band()` helper from C4 in C5–C7.

### C5: Update translation priority (snapshots)

- **Status**: Pending
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 3–7 (parallel with C4, C6, C7)
- **Blocked by**: C1, C2
- **Branch**: `local/c5-snapshot-priority`
- **Integration date**: —
- **Commits**: —
- **Gate result**: —
- **Conflicts**: —
- **Notes**: Same priority formula as C4, but for pages (snapshots) instead of candidates. Groups by `catalogue_service_id` instead of `candidate_id`.

### C6: Update embedding priority & phase tracking

- **Status**: Pending
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 3–7 (parallel with C4, C5, C7)
- **Blocked by**: C1, C2
- **Branch**: `local/c6-embedding-phase`
- **Integration date**: —
- **Commits**: —
- **Gate result**: —
- **Conflicts**: —
- **Notes**: Embedding priority uniform within pipeline (100), but phase component added for consistency. Phase auto-advances to 2 when all candidates have embeddings.

### C7: Update discovery task selection

- **Status**: Pending
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 3–7 (parallel with C4, C5, C6)
- **Blocked by**: C1, C2
- **Branch**: `local/c7-discovery-phase`
- **Integration date**: —
- **Commits**: —
- **Gate result**: —
- **Conflicts**: —
- **Notes**: Extends discovery with phase component. Page completeness tie-break (D7) preserved; phase is a separate layer above it.

### C8: Modify `LeasedQueue.claim()` for phase/grouping

- **Status**: Pending
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 8–9
- **Blocked by**: C2, C3, C4, C5, C6, C7 (all integrated)
- **Branch**: `local/c8-leased-queue-integration`
- **Integration date**: —
- **Commits**: —
- **Gate result**: —
- **Conflicts**: —
- **Notes**: Generic queue base class modified to support phase and grouping. All four pipelines (translation, snapshot, embedding, discovery) updated to pass grouping field.

### C9: Add observability & metrics

- **Status**: Pending
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 10
- **Blocked by**: C3, C4, C5, C6, C7, C8 (all integrated)
- **Branch**: `local/c9-metrics-observability`
- **Integration date**: —
- **Commits**: —
- **Gate result**: —
- **Conflicts**: —
- **Notes**: Prometheus metrics for phase state, queue health, coverage %. Emissions occur at state transitions and task settlements. Pipeline-aware metrics with labels.

### C10: End-to-end integration & validation

- **Status**: Pending
- **Assigned to**: chapter-implementer
- **Scheduled**: Day 10–13
- **Blocked by**: C3, C4, C5, C6, C7, C8, C9 (all integrated)
- **Branch**: `local/c10-integration-validation`
- **Integration date**: —
- **Commits**: —
- **Gate result**: —
- **Conflicts**: —
- **Notes**: Three integration tests (breadth-first ordering, phase transitions, coverage tracking) + stress test + rollback validation. Final gate before release.

## Release Gate

**Status**: Pending all chapters integrated

**Pre-Release Checklist**:
- [ ] All 10 chapters integrated into loop branch
- [ ] Full test suite passes: `pytest`
- [ ] Lint clean: `ruff check`, `ruff format --check`
- [ ] Type check clean: `mypy`
- [ ] C10 integration tests pass with green metrics
- [ ] No task starvation observed in metrics
- [ ] Phase transitions happen automatically
- [ ] Coverage increases monotonically in phase 1

**Release Steps** (chief-of-staff only):
1. Merge loop branch into release branch
2. Create release PR to main
3. Wait for CI
4. Merge to main
5. Tag release

## Actual Timings

(To be filled as chapters complete)

| Chapter | Estimated | Actual | Delta |
|---------|-----------|--------|-------|
| C1 | 2 days | — | — |
| C2 | 2 days | — | — |
| C3 | 1 day | — | — |
| C4–C7 | 5 days | — | — |
| C8 | 2 days | — | — |
| C9 | 1 day | — | — |
| C10 | 3 days | — | — |
| **Total** | **~16 days** | — | — |

## Known Risks & Mitigations

| Risk | Probability | Impact | Mitigation | Status |
|------|----|----|---|---|
| Phase transition logic has off-by-one error | Medium | Stalls work | C10 integration tests catch this; manual override in C3 during C10 | Mitigated by C10 |
| Priority formula breaks compatibility | Low | Old tasks stuck | Backfill migration in C2; C8 handles gracefully | Mitigated by C2, C8 |
| State table grows too large | Low | Query slowdown | Add index on (entity_id, pipeline); partition if >1M rows | Monitored by C9 metrics |
| Coverage tracking drifts | Medium | Stalls phase 1→2 transition | C3 includes periodic audit; C9 metrics expose drift | Mitigated by C3, C9 |

## Notes

- **Loop branch**: `feat/plans-pipeline-optimisation` (current working branch)
- **Release branch**: `main` (target for release PR)
- **Local integration**: Each chapter merges to loop branch locally; chief-of-staff orchestrates
- **Remote CI**: Runs on release PR and tags only; no per-chapter remote CI
- **Parallelization**: Batches 1–4 as defined; use independent worktrees to avoid conflicts
