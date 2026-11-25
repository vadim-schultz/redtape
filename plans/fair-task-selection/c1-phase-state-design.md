---
id: C1
depends_on: []
touches:
  - plans/fair-task-selection/
execution: chapter-implementer
---

# C1: Phase-State Machine & Priority Formula Design

## Goal

Design and document the phase-state machine, priority formula, and coverage tracking mechanism that will be implemented in C2–C10.

## Acceptance Criteria

- ✅ Phase-state diagram with transitions and rules documented
- ✅ Priority formula proven to prevent starvation
- ✅ Coverage bitmap design validated against expected workload (4000 candidates, 10 locales)
- ✅ All assumptions documented (e.g., "Phase 1 completes in <N days at <throughput>")
- ✅ Design reviewed and approved by chief of staff

## Scope

**What's in C1:**
- State machine diagram (Graphviz or ASCII)
- Priority formula derivation and justification
- Coverage tracking design (bitmap or table)
- Transition rules (auto-trigger conditions)
- Performance estimates
- Design doc (Markdown, to be included in release notes)

**What's NOT in C1:**
- Code implementation (that's C2–C8)
- Deployment procedures (covered in release)
- Worker configuration (separate)

## Implementation Plan

### Slice 1: State Machine Diagram

**Red**: Write two tests (one happy, one negative):

1. **Happy path**: Given state machine rules, verify that phase transitions in the correct order
   - Start: phase 1, 10 documents, 0 completed
   - Enqueue 100 tasks (high + low confidence mixed)
   - Claim & complete 50 tasks for first document
   - Assert: phase still 1 (not all documents touched)
   - Claim & complete 50 tasks for remaining 9 documents (1 each per locale)
   - Assert: phase transitions to 2 (all documents touched once)

2. **Negative path**: Verify phase 1 → 2 doesn't happen prematurely
   - Enqueue 100 tasks for 10 documents (10 each)
   - Complete only 50 tasks (5 documents, 1 locale each)
   - Assert: phase remains 1 (not all documents covered)
   - Assert: future claims still pick phase 1 items (high-confidence items don't jump to phase 2)

**Green**: ASCII state machine diagram with labeled transitions

```
Phase 1 (Breadth-First)
  ↓ [all documents have ≥1 completed task per locale]
Phase 2 (Depth-First)
  ↓ [all phase 2 tasks completed OR timeout]
Phase 3 (Refresh)
  ↓ [all phase 3 tasks completed]
Loop back to Phase 1 (optional: restart cycle)
```

**Refactor**: Check for missing states, loops, or timeout conditions.

### Slice 2: Priority Formula Derivation

**Red**: Two tests:

1. **Happy path**: Verify priority formula produces correct ordering
   - Scenario: 3 candidates (A: high conf, B: low conf, C: high conf), 3 locales each, all phase 1
   - Assert: Claim produces A[en], A[de], A[fr], B[en], B[de], B[fr], C[en], C[de], C[fr] order
   - Assert: Within same phase, grouping by candidate (not confidence)

2. **Negative path**: Phase 2 items never claim before phase 1 complete
   - Scenario: 1 candidate (high conf) in phase 2, 1 candidate (low conf) in phase 1
   - Assert: Phase 1 candidate's tasks claim before phase 2 candidate's tasks

**Green**: Formula document:

```
priority = (phase * 100_000) + (confidence_rank * 100) + (locale_index)

Where:
  phase ∈ {0, 1, 2} → {0, 100_000, 200_000}
  confidence_rank = 1000 - round(confidence * 1000)
  locale_index = 0–99 (stable)
```

Proof: Within phase 1, all items range 0–99,999; phase 2 items range 100,000+; impossible to invert.

**Refactor**: No duplication detected; formula is minimal.

### Slice 3: Coverage Tracking Design

**Red**: Two tests:

1. **Happy path**: Coverage bitmap tracks completion correctly
   - Scenario: Document D, pipeline Translation, 10 locales
   - Enqueue 10 tasks (one per locale)
   - Settle task for locale [en], [de]
   - Assert: bitmap = 0b0000000011 (en=bit0, de=bit1 set)
   - Query: "Is document D phase-1 complete?" → Check if all 10 bits set

2. **Negative path**: Coverage doesn't count claimed-but-incomplete tasks
   - Scenario: Same document, claim task for [fr] but don't settle
   - Assert: bitmap still = 0b0000000011 (fr=bit2 unset)
   - Assert: Document D remains phase 1 (not all locales complete)

**Green**: Table design and algorithm:

```sql
CREATE TABLE fair_selection_state (
  id UUID PRIMARY KEY,
  pipeline TEXT NOT NULL, -- 'translation', 'embedding', etc.
  entity_id UUID NOT NULL, -- candidate_id or catalogue_service_id
  phase INTEGER DEFAULT 1,
  coverage_bitmap BIGINT DEFAULT 0, -- bits 0–63 → locales 0–63
  updated_at TIMESTAMP DEFAULT NOW()
);
```

Algorithm:
- On task settlement: `UPDATE fair_selection_state SET coverage_bitmap = coverage_bitmap | (1 << locale_index) WHERE entity_id = ? AND pipeline = ?`
- Phase 1 → 2 trigger: Count rows where `coverage_bitmap = (1 << num_locales) - 1`

**Refactor**: Check if 64-bit bitmap sufficient (10 locales → ✅ fits); document assumption.

### Slice 4: Transition Rules & Performance

**Red**: Two tests:

1. **Happy path**: Auto-transition triggers correctly
   - Scenario: 10 documents, 10 locales each, 100 total tasks
   - Settle 100 tasks (all documents, all locales)
   - Assert: phase auto-transitions to 2
   - Assert: Subsequent claims pick phase 2 tasks (confidence-ranked)

2. **Negative path**: Partial completion doesn't trigger transition
   - Scenario: 10 documents, complete only 95 tasks (9.5 documents)
   - Assert: phase remains 1
   - Assert: Transition doesn't happen until last task complete

**Green**: Transition rules doc:

```
Phase 1 → 2:
  Trigger: COUNT(*) FROM fair_selection_state WHERE phase=1 AND coverage_bitmap != (1 << num_locales)-1 == 0
  Action: UPDATE fair_selection_state SET phase = 2 WHERE phase = 1
  Cadence: Check on each task settlement (or batch settle)

Phase 2 → 3 or 1:
  Trigger: No pending tasks with phase=2, AND any phase=3 tasks exist
  Action: Optionally set phase=3; or restart cycle (phase=1 for next batch of candidates)
  Cadence: Periodic check (hourly or on-demand)
```

Performance estimate:
- 4000 candidates × 10 locales = 40,000 tasks
- Throughput: ~100 tasks/hour (from observed worker drain rates)
- Phase 1 duration: ~400 hours = ~17 days
- Acceptable: Gives fair coverage within reasonable time

**Refactor**: No code yet; just documentation. Check for missing edge cases (new candidates enqueued during phase 1, etc.).

### Slice 5: Design Document (Release Notes)

**Red**: Two tests:

1. **Happy path**: Design doc is readable by non-implementers
   - Write a one-page summary (problem, solution, timeline)
   - Proof-read: Check for typos, unclear sections, missing diagrams

2. **Negative path**: Design doc doesn't have implementation details that might leak into user docs
   - Assert: No SQL, no Python code in the user-facing section
   - Assert: Business logic (phase transitions) explained in plain English

**Green**: Write release notes snippet:

```markdown
## Fair Task Selection Strategy

Redtape now ensures all documents get fair coverage before prioritizing high-confidence items.

**What changed**: Task queues now operate in three phases:
1. Breadth-first: Every document gets ≥1 task attempted
2. Depth-first: Remaining work completed by confidence
3. Refresh: New versions re-enqueued

This prevents low-confidence documents from starving indefinitely.

**Timeline**: Breadth-first phase takes ~2–3 weeks for full coverage. No action needed; selection is automatic.
```

**Refactor**: Check clarity; remove internal jargon.

## Test Output

**After this chapter**:
- `plans/fair-task-selection/00-architecture.md` (updated with Slice 2–3 details)
- `docs/FAIR_SELECTION_DESIGN.md` (Slice 5 output)
- Diagram file (Graphviz or image)

## Gate

✅ Local: `pytest tests/features/fair_selection/test_state_machine.py` (all 5 slices)
✅ Full: `scripts/ci.sh` (overall lint & format)

## Notes

- State machine assumes candidates don't get deleted (tombstone if needed)
- Phase 1 duration depends on throughput; monitor and adjust timeout if needed
- Coverage bitmap assumes ≤64 locales; if more added, switch to BYTEA or separate table
