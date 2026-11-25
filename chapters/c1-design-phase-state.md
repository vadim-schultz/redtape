---
name: Chapter C1 - Design Phase-State Machine & Priority Formula
overview: "Design and document the phase-state machine, priority formula, and coverage tracking mechanism that enables fair task selection across redtape pipelines."
id: C1
depends_on: []
touches:
  - plans/fair-task-selection/
execution: chapter-implementer
isProject: false
---

# C1 - Design Phase-State Machine & Priority Formula

**Depends on:** None · **Architecture:** `/mnt/projects/redtape/plans/fair-task-selection/00-architecture.md` · **Rollout:** `/mnt/projects/redtape/plans/fair-task-selection/01-rollout.md`

## Goal

Document the three-phase task selection strategy (breadth-first, depth-first, refresh), the priority formula that enforces phase ordering, and the coverage tracking design that enables state transitions. This design prevents low-confidence documents from starving indefinitely while maintaining throughput.

## Read first

- **00-architecture.md**: Problem statement (section "Current problem"), solution overview (section "Solution: Three-Phase Selection Strategy"), and pipeline-specific changes summary. If this chapter and the architecture disagree, the architecture wins.
- **01-rollout.md**: Chapter schedule matrix and per-chapter gate expectations.

## Coordination scope

**Add:**

- `/mnt/projects/redtape/docs/FAIR_SELECTION_DESIGN.md` — User-facing design summary (Slice 5 output)
- State machine diagram (ASCII or Graphviz format, included in design doc)

**Edit:**

- `/mnt/projects/redtape/plans/fair-task-selection/00-architecture.md` — Add Slice 2 priority formula proof and Slice 3 coverage bitmap implementation details

**Do not edit:**

- `/mnt/projects/redtape/apps/api/app/features/translation/priority.py` — owned by C4
- `/mnt/projects/redtape/apps/api/app/features/search/enqueue.py` — owned by C6
- Database schema files — owned by C2

## Work items

### Slice 1: State Machine Diagram

**Red test**

1. **Happy path** (`test_state_machine_transitions_breadth_to_depth`): Verify state machine transitions correctly when phase-1 coverage completes
   - Setup: 10 documents, 10 locales per document, all in phase 1 with zero coverage
   - Action: Mark all documents as having ≥1 completed task per locale (simulated completion)
   - Assert: Phase transitions to 2 (all documents breadth-first complete)
   - Assert: Subsequent task claims pick phase-2 items (confidence-ranked, not phase-1 breadth-grouped)

2. **Negative path** (`test_state_machine_blocks_premature_transition`): Verify phase 1 → 2 doesn't happen until all documents covered
   - Setup: 10 documents, 10 locales per document
   - Action: Complete coverage only for 5 documents (50 locales touched, 50 untouched)
   - Assert: Phase remains 1 (not all documents have full locale coverage)
   - Assert: Future task claims still pick phase-1 items (high-confidence items don't jump to phase 2 early)

**Green implementation**

ASCII state machine diagram (placed in design doc):

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Breadth-First Coverage                             │
│ • Every document gets ≥1 task attempted per locale          │
│ • Priority: (phase=0 * 100,000) + (confidence_rank * 100)   │
│ • Transition trigger: All documents have full locale bitmap  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   [all docs 100% complete
                    per locale bitmap]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Depth-First Completion                             │
│ • Complete remaining work by confidence score               │
│ • Priority: (phase=1 * 100,000) + (confidence_rank * 100)   │
│ • Transition trigger: No pending phase-2 tasks              │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   [phase 2 complete OR
                    timeout: 48 hours]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Refresh Mode                                       │
│ • Re-enqueued work (source or candidate data changed)       │
│ • Priority: (phase=2 * 100,000) + (confidence_rank * 100)   │
│ • Transition trigger: Cycle restart or manual override      │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   [optional: restart to
                    Phase 1 for next batch]
```

Transition table:

| Current Phase | Trigger | Next Phase | Action |
|---------------|---------|------------|--------|
| 1 | All documents have coverage bitmap = (1 << num_locales) - 1 | 2 | UPDATE fair_selection_state SET phase = 2 WHERE phase = 1 |
| 2 | No pending tasks with phase = 2 AND phase-3 tasks exist | 3 | UPDATE fair_selection_state SET phase = 3 WHERE phase = 2 |
| 2 | Timeout (48 hours) OR manual cycle restart | 1 | Enqueue new batch; existing phase-2 items age out or archive |
| 3 | Manual cycle restart | 1 | Enqueue new batch |

**Refactor audit**

- ✅ **~5 LOC** per unit: Diagram is documentation; no code size to audit yet. No duplication detected.
- ✅ **State coverage**: Three phases, two transitions documented. No missing states or loops.
- ✅ **Edge cases noted**: New documents enqueued during phase 1 handled by C3 (state transition logic). Timeouts noted for C3 implementation. Bitmap width assumption documented (≤64 locales, rationale below).

---

### Slice 2: Priority Formula Derivation

**Red test**

1. **Happy path** (`test_priority_formula_enforces_phase_ordering`): Verify priority formula produces correct within-phase and across-phase ordering
   - Setup: 3 candidates (A: confidence 0.9, B: confidence 0.3, C: confidence 0.95), 3 locales each, all phase 1
   - Action: Compute priority for all 9 tasks; sort ascending
   - Assert: Order is A[en], A[de], A[fr], B[en], B[de], B[fr], C[en], C[de], C[fr] (grouping by candidate within phase 1)
   - Assert: Within same candidate, stable locale ordering (en < de < fr, alphabetic)

2. **Negative path** (`test_priority_formula_blocks_phase2_until_phase1_complete`): Verify phase-2 items never claim before phase-1 items complete
   - Setup: 1 candidate (A: confidence 0.95, phase 2), 1 candidate (B: confidence 0.1, phase 1), 3 locales each
   - Action: Compute priority for all 6 tasks; sort ascending
   - Assert: All phase-1 (B) tasks claim before any phase-2 (A) tasks
   - Assert: Phase-1 priority range (0–99,999) < phase-2 range (100,000–199,999) (no overlap)

**Green implementation**

Priority formula specification (placed in architecture.md):

```
priority = (phase_component * 100_000) + (confidence_rank * 100) + locale_index

Where:
  phase ∈ {1, 2, 3} → phase_component ∈ {0, 1, 2}

  confidence_rank = 1000 - round(confidence * 1000)
    • confidence ∈ [0.0, 1.0]
    • higher confidence → lower confidence_rank → lower priority value → claims first
    • confidence 0.0 → rank 1000, confidence 1.0 → rank 0

  locale_index ∈ [0, 99]
    • Assigned once per locale; stable across rebalance
    • Example: en=0, de=1, fr=2, ... (alphabetic order)
    • Within same (phase, confidence_rank), stable tie-break
```

**Proof of correctness**:

- Phase 1 priority range: 0–99,999 (phase_component=0, confidence_rank ∈ [0, 1000], locale_index ∈ [0, 99])
- Phase 2 priority range: 100,000–199,999 (phase_component=1, same confidence_rank and locale_index ranges)
- Phase 3 priority range: 200,000–299,999 (phase_component=2, same ranges)

**Proof that within-phase ordering is stable**: For any two tasks with the same phase and confidence_rank, locale_index is the final tie-break. Locale indices are assigned at database schema time (e.g., 0='en', 1='de') and never change. Thus no two tasks compete with identical (phase, confidence_rank, locale_index) tuples.

**Proof that starvation is prevented**: Any phase-1 task has priority < 100,000; any phase-2 task has priority ≥ 100,000. Because work is claimed in ascending priority order, all phase-1 work must complete before phase-2 starts. Within phase 1, each document is grouped (via LeasedQueue grouping parameter) so all locales of one document are claimed together, ensuring even the lowest-confidence documents get coverage within ~40,000 / throughput time (40,000 candidate-locales across all pipelines; observed throughput ~100/hr → ~17 days for phase 1).

**Refactor audit**

- ✅ **Formula minimality**: No redundant components; (phase, confidence_rank, locale_index) is the minimal sufficient set.
- ✅ **No duplication**: Formula applies uniformly across all pipelines (translation, embedding, discovery).
- ✅ **Assumption documented**: Assumes ≤100 locales (locale_index fits in [0, 99]). If more locales added, increase width to [0, 999], adjust constants accordingly (see C2 migration for future-proofing).

---

### Slice 3: Coverage Tracking Design

**Red test**

1. **Happy path** (`test_coverage_bitmap_tracks_per_locale_completion`): Verify coverage bitmap correctly reflects which locales have completed tasks
   - Setup: Document D, pipeline 'translation', 10 locales (en, de, fr, es, it, pt, nl, pl, ru, ja)
   - Action: Enqueue 10 tasks (one per locale); settle tasks for locales en, de
   - Assert: bitmap = 0b0000000011 (en=bit0, de=bit1 set, all others unset)
   - Assert: Query "is document D phase-1 complete?" returns False (8 locales still pending)

2. **Negative path** (`test_coverage_bitmap_ignores_claimed_unfinished_tasks`): Verify that claiming a task doesn't mark coverage until settled
   - Setup: Document D, same 10 locales
   - Action: Enqueue 10 tasks; claim (but don't settle) task for locale fr
   - Assert: bitmap = 0b0000000000 (no bits set; fr claim doesn't count)
   - Assert: Query "is document D phase-1 complete?" returns False (all 10 locales still pending, despite fr being claimed)

**Green implementation**

Data model (table definition for C2 to implement):

```sql
CREATE TABLE fair_selection_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pipeline TEXT NOT NULL,
    -- Enum: 'translation', 'embedding', 'discovery', 'screenshots'
  entity_id UUID NOT NULL,
    -- candidate_id or catalogue_service_id
  phase INTEGER NOT NULL DEFAULT 1,
    -- 1=breadth-first, 2=depth-first, 3=refresh
  coverage_bitmap BIGINT NOT NULL DEFAULT 0,
    -- Bit vector; bit N set when locale N has ≥1 settled task
    -- Max 64 bits → up to 64 locales (current: 10, headroom for growth)
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),

  CONSTRAINT coverage_bitmap_non_negative CHECK (coverage_bitmap >= 0),
  UNIQUE (pipeline, entity_id)
);

CREATE INDEX ix_fair_selection_state_phase ON fair_selection_state(phase);
CREATE INDEX ix_fair_selection_state_entity ON fair_selection_state(entity_id, pipeline);
```

Coverage algorithm (pseudocode for C3 to implement):

```python
def on_task_settled(pipeline: str, entity_id: UUID, locale_index: int):
    """Mark locale as covered when any task settles (success or failure)."""
    # Set bit locale_index in coverage_bitmap
    sql = """
    UPDATE fair_selection_state
    SET coverage_bitmap = coverage_bitmap | (1 << %s),
        updated_at = NOW()
    WHERE entity_id = %s AND pipeline = %s
    """
    execute(sql, (locale_index, entity_id, pipeline))

def is_phase1_complete(pipeline: str) -> bool:
    """Check if all documents have full locale coverage."""
    expected_bitmap = (1 << get_num_locales(pipeline)) - 1
    sql = """
    SELECT COUNT(*) FROM fair_selection_state
    WHERE pipeline = %s AND phase = 1 AND coverage_bitmap != %s
    """
    incomplete_count = execute(sql, (pipeline, expected_bitmap)).scalar()
    return incomplete_count == 0

def reset_coverage_on_phase_transition(pipeline: str):
    """Reset coverage bitmap when transitioning to phase 2 (optional; depends on design choice)."""
    # Option A: Keep bitmap (track "ever touched"); useful for audits
    # Option B: Reset to 0 (measure only phase-2 coverage)
    # Recommendation: Keep bitmap; phase-2 coverage is implicit (no new bitmap requirement)
    pass
```

**Bitmap width justification**: Current redtape deployment has 10 locales (en, de, fr, es, it, pt, nl, pl, ru, ja). A 64-bit BIGINT supports up to 64 locales, providing 6× headroom. If ever more than 64 locales needed, migrate to `BYTEA` (variable-width bit vector) in a future chapter.

**Refactor audit**

- ✅ **Table simplicity**: Three columns (entity_id, pipeline, phase, coverage_bitmap) represent the minimal state needed for phase transitions. No redundancy.
- ✅ **Index strategy**: (phase) index supports phase-transition queries; (entity_id, pipeline) supports per-document lookups.
- ✅ **Assumption documented**: 64-bit bitmap limit and migration path documented above.

---

### Slice 4: Transition Rules & Performance

**Red test**

1. **Happy path** (`test_phase1_to_phase2_transition_triggers_automatically`): Verify automatic phase transition when all documents achieve full coverage
   - Setup: 10 documents, 10 locales each, 100 total tasks in phase 1
   - Action: Settle all 100 tasks (all documents, all locales); trigger transition check
   - Assert: Phase auto-transitions to 2 (UPDATE fair_selection_state SET phase = 2 WHERE phase = 1)
   - Assert: Subsequent claims pick phase-2 tasks (priority range 100,000+)

2. **Negative path** (`test_phase1_to_phase2_transition_blocks_on_incomplete_coverage`): Verify no transition until every document is fully covered
   - Setup: 10 documents, 10 locales each; settle 95 tasks (9.5 documents)
   - Action: Trigger transition check on 95-task state
   - Assert: Phase remains 1 (COUNT(*) FROM fair_selection_state WHERE phase=1 AND coverage_bitmap != 0x3FF > 0)
   - Assert: Transition doesn't happen until last task settles

**Green implementation**

Transition rules (algorithmic specification for C3 to implement):

```
Transition Phase 1 → 2:
  Trigger: Periodic check (on each task settlement in high-volume pipelines;
           or hourly batch check in low-volume pipelines)

  Condition:
    SELECT COUNT(*) FROM fair_selection_state
    WHERE pipeline = %s AND phase = 1
      AND coverage_bitmap != (1 << num_locales) - 1
    == 0

    (i.e., no documents in phase 1 with incomplete coverage)

  Action:
    UPDATE fair_selection_state
    SET phase = 2, updated_at = NOW()
    WHERE pipeline = %s AND phase = 1

  Cadence: Check on each task settlement (immediate transition)
           or batch check every 5 minutes (batch transition)
           Recommendation: Immediate check for tight fairness;
           batch check if query load is unacceptable


Transition Phase 2 → 3 or Restart:
  Trigger: Periodic check (hourly or on-demand)

  Condition:
    SELECT COUNT(*) FROM fair_selection_state
    WHERE pipeline = %s AND phase = 2
      AND EXISTS (SELECT 1 FROM tasks WHERE ... AND phase = 2 AND status = 'pending')

    (i.e., no pending phase-2 tasks remain)

  Action (Option A):
    UPDATE fair_selection_state
    SET phase = 3, updated_at = NOW()
    WHERE pipeline = %s AND phase = 2

    (Begin refresh phase; re-enqueued items are marked phase 3)

  Action (Option B):
    DELETE FROM fair_selection_state WHERE pipeline = %s

    (Reset for next batch; new documents enqueued as phase 1)

  Recommendation: Option B (reset) for simpler lifecycle;
                  Option A (phase 3) for audit trail and refresh semantics


Timeout & Manual Override:
  Phase 2 timeout: If phase 2 duration exceeds 48 hours,
    administrator can force Phase 3 or restart via manual override.

  Trigger: Cron job or on-demand (e.g., after long weekend)
  Action: UPDATE fair_selection_state SET phase = 3 WHERE pipeline = %s AND phase = 2
```

Performance estimate (from architecture.md):

```
Scenario: Translation pipeline, one cycle

Assumptions:
  • 4000 candidate documents
  • 10 locales per candidate
  • 100 total tasks (candidate-locales across all pipelines, shared)
  • Observed throughput: ~100 tasks/hour (from worker drain rates)

Phase 1 (Breadth-First):
  Scope: 4000 × 10 = 40,000 candidate-locale pairs
  Duration: 40,000 / 100 per hour = 400 hours = ~17 days
  Fairness: Every low-confidence candidate gets coverage in <17 days

Phase 2 (Depth-First):
  Scope: Remaining work on partially-done candidates (varies by pipeline)
  Assumption: ~50% of phase-1 work was partial (1 task/candidate settled in phase 1)
  Duration: Remaining = 2,000 tasks (5% of phase 1) + retranslations (~10% per pipeline)
  Estimate: ~200 hours = ~8 days (confidence-ranked, so high-confidence candidates finish faster)

Phase 3 (Refresh):
  Scope: New candidates or refreshed source data
  Duration: Same as phase 2 (ongoing)

Total cycle: ~25 days (17 phase-1 + 8 phase-2)
Acceptable: Fairness achieved within monthly business cycle
```

**Refactor audit**

- ✅ **Rule clarity**: Transition conditions specified algorithmically; no ambiguity.
- ✅ **Performance documented**: Phase durations and throughput assumptions laid out for future monitoring (C9 metrics).
- ✅ **Edge case handling**: Manual override and timeout documented for C3 implementation.

---

### Slice 5: Release Notes & User-Facing Documentation

**Red test**

1. **Happy path** (`test_design_doc_is_accessible_to_non_implementers`): Verify design documentation is readable and self-contained
   - Create one-page summary covering problem, solution, timeline, and impact
   - Proof-read: Check for typos, unclear sections, unexplained terms
   - Assert: Proof-reader (product manager or ops) can explain the three phases and timeline without reading architecture.md
   - Assert: No code or SQL visible in user-facing section

2. **Negative path** (`test_design_doc_excludes_implementation_details`): Verify no internal details leak into release notes
   - Assert: No SQL, Python function names, or database column names
   - Assert: No "bitmap" or "priority = phase * 100,000" formulas (too internal)
   - Assert: Business logic (fairness, timeline) explained in business terms, not technical terms

**Green implementation**

Release notes snippet (placed in `/mnt/projects/redtape/docs/FAIR_SELECTION_DESIGN.md`):

```markdown
# Fair Task Selection Strategy

Redtape now ensures all documents get equal coverage before prioritizing high-confidence items.

## What changed

Task queues now operate in three phases:

1. **Breadth-First Coverage** (~2–3 weeks)
   Every document gets at least one task completed per language. This prevents low-confidence documents from waiting indefinitely while high-confidence work repeats.

2. **Depth-First Completion** (~1 week)
   Remaining work is completed by confidence score. High-confidence documents get more resources, but low-confidence documents already have baseline coverage.

3. **Refresh Mode** (ongoing)
   New or updated documents are re-enqueued and processed through the same phases.

## Why this matters

**Before**: Low-confidence documents often never received translation or embedding work because high-confidence documents were retranslated repeatedly.

**After**: Every document is guaranteed coverage in <3 weeks; high-confidence documents get additional work afterward.

## Timeline

- Breadth-first phase: ~17 days (40,000 candidate-language pairs ÷ 100 tasks/hour observed)
- Depth-first phase: ~8 days (remaining high-confidence retranslations)
- **Total**: ~25 days per cycle

No action needed; phase transitions happen automatically.

## Monitoring

Check the redtape dashboard for phase status and completion percentage:
- **Phase 1 progress**: % of documents with baseline coverage
- **Phase 2 progress**: % of documents with final confidence-ranked work
- **Cycle timeline**: Auto-advances when phase milestones hit

Questions? Contact the redtape team.
```

**Additional artifacts**:

- State machine diagram (from Slice 1) embedded in design doc or as separate `/mnt/projects/redtape/docs/FAIR_SELECTION_STATE_DIAGRAM.txt`
- Performance estimates table (from Slice 4) included in monitoring section

**Refactor audit**

- ✅ **Clarity**: Avoids jargon (no "bitmap," "confidence_rank," or SQL); uses business terms ("baseline coverage," "high-confidence retranslations").
- ✅ **Completeness**: Problem (before), solution (after), timeline, and action items all present in <1 page.
- ✅ **Audience**: Product managers and operators can read and understand timeline impact; no implementation details leak.

---

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| State machine transitions | `test_state_machine_transitions_breadth_to_depth` | `test_state_machine_blocks_premature_transition` |
| Priority formula ordering | `test_priority_formula_enforces_phase_ordering` | `test_priority_formula_blocks_phase2_until_phase1_complete` |
| Coverage bitmap tracking | `test_coverage_bitmap_tracks_per_locale_completion` | `test_coverage_bitmap_ignores_claimed_unfinished_tasks` |
| Phase 1→2 transition | `test_phase1_to_phase2_transition_triggers_automatically` | `test_phase1_to_phase2_transition_blocks_on_incomplete_coverage` |
| Release documentation | `test_design_doc_is_accessible_to_non_implementers` | `test_design_doc_excludes_implementation_details` |

## Review gate

Before merging this chapter:

1. ✅ All 10 tests pass (5 slices × 2 tests each)
2. ✅ State machine diagram is clear and unambiguous (review by tech lead)
3. ✅ Priority formula proof is mathematically correct (peer review by another engineer)
4. ✅ Coverage bitmap design handles edge cases (review for off-by-one errors, bitmap width limits)
5. ✅ Performance estimates are justified (review against observed worker throughput logs)
6. ✅ Release notes are readable by non-technical stakeholders (review by product manager)
7. ✅ No implementation details in user-facing docs (lint: no SQL, no Python function names, no formulas)
8. ✅ Architecture file updated with Slice 2 formula and Slice 3 bitmap details
9. ✅ `scripts/ci.sh lint` passes (docstring check, format, type hints)
10. ✅ No broken cross-references to other chapters (C2–C10 files don't exist yet; OK)

## Out of scope

- **Code implementation** — C2 (schema), C3 (state logic), C4–C7 (pipeline priorities), C8 (queue integration)
- **Worker configuration** — Separate runbook (not in this work package)
- **Deployment procedures** — Covered in release chapter

## Verification

```bash
# From repository root; run all five test slices
pytest tests/features/fair_selection/ -v

# Verify design doc exists and is well-formatted
ls -lh docs/FAIR_SELECTION_DESIGN.md
head -20 docs/FAIR_SELECTION_DESIGN.md

# Verify no implementation leaks into docs
grep -i "bitmap\|sql\|def \|priority =" docs/FAIR_SELECTION_DESIGN.md || echo "✓ No implementation details found"

# Verify architecture.md was updated with formula and bitmap details
grep -A5 "priority_formula" plans/fair-task-selection/00-architecture.md
grep -A10 "coverage_bitmap" plans/fair-task-selection/00-architecture.md

# Full lint check
scripts/ci.sh lint
```

Expected:
- All 10 pytest tests pass with 2 passed per slice
- Design doc exists and is readable
- No grep hits for implementation terms
- Architecture.md contains updated Slice 2 formula and Slice 3 bitmap sections
- `scripts/ci.sh lint` exits 0 (docstring/format/type checks pass)

## Refactor report

No refactor needed — this chapter is design documentation only. Each slice is a focused specification:
- Slice 1: State machine (1 diagram + 1 transition table, minimal duplications handled)
- Slice 2: Priority formula (1 formula + 1 proof, no code)
- Slice 3: Coverage design (1 table schema + 1 algorithm, no code)
- Slice 4: Transition rules (1 trigger spec + 1 performance estimate, no code)
- Slice 5: Release notes (1 summary + 1 artifact list, plain language)

No classes, no methods, no branch count exceeds limits. Documentation is clear and self-contained.

## Git workflow

- Check out the loop branch: `git checkout feat/plans-pipeline-optimisation` (or the chapter's loop branch if assigned)
- Create the chapter branch: `git checkout -b c1-design-phase-state`
- Commit the red tests first: Tests are documentation in this chapter; commit design specs as single commit
- Run the local gate: `scripts/ci.sh lint` (documentation passes if no format/docstring errors)
- Do not push; do not open a pull request. The chief-of-staff merges this chapter into the loop branch after C2 (schema) is ready.
