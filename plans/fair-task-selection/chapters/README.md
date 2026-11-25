# Fair Task Selection - Implementation Chapters

This directory contains the implementation chapters for the fair task selection work package. Each chapter is an independent, self-contained unit of work following the TDD red → green → refactor workflow.

## Chapter Overview

| ID | Title | Status | Dependencies |
|----|-------|--------|--------------|
| C1 | Design phase-state machine & priority formula | — | — |
| C2 | Create `fair_selection_state` table & migration | — | C1 |
| C3 | Implement state transition logic | — | C2 |
| C4 | Update translation priority (candidates) | — | C1, C2 |
| C5 | Update translation priority (snapshots) | — | C1, C2 |
| C6 | Update embedding priority & phase tracking | — | C1, C2 |
| C7 | Update discovery task selection | — | C1, C2 |
| C8 | Modify `LeasedQueue.claim()` for phase/grouping | — | C2, C3, C4, C5, C6, C7 |
| C9 | Add observability & metrics | — | C3–C8 |
| C10 | End-to-end integration & validation | — | C3–C9 |

## Execution Model

Each chapter:
1. ✅ Runs locally on an isolated worktree (chapter branch)
2. ✅ Passes local gate: `scripts/ci.sh` (lint, type check, tests)
3. ✅ Integrates into the loop branch with `git merge --no-ff` (no rebase)
4. ✅ Reports: paired tests, refactor outcome, local gate result
5. ❌ Never pushes or opens a PR (chief-of-staff handles integration)

## Parallel Batches

**Batch 1 (Days 1–2)**: C1, C2
- C1 is design docs (no code)
- C2 is schema (no business logic)

**Batch 2 (Days 3–7)**: C3, C4, C5, C6, C7
- C3 enables state management
- C4–C7 each update a pipeline independently (no conflicts)

**Batch 3 (Days 8–9)**: C8
- Integrates all pipeline priorities into generic queue

**Batch 4 (Days 10–13)**: C9, C10
- C9 adds observability
- C10 validates system

## Local Gate

For each chapter:
```bash
./scripts/ci.sh
```

## How to Read This

1. Start with `00-architecture.md` and `01-rollout.md` for context
2. Read each chapter in dependency order (C1, C2, C3, then C4–C7 in any order, etc.)
3. For each chapter:
   - Read the **Goal** and **Acceptance Criteria** to understand the target
   - Review each **Slice** (5 per chapter) with its red, green, and refactor phases
   - Check the **Gate** to verify it's testable
4. Implement following TDD: write red tests first (both fail), then green (both pass), then refactor (no new tests)

## Common Patterns

### Reading Phase from Database
```python
from app.features.fair_selection.source import get_phase_for_candidate

phase = get_phase_for_candidate(session, candidate_id)
# Returns: 1 (default) if not found, or the actual phase (1–3)
```

### Phase Component in Priority
```python
def _phase_band(phase: int) -> int:
    """Convert phase (1–3) to priority band offset."""
    return (phase - 1) * 100_000

def first_priority(confidence: float, phase: int = 1) -> int:
    return _phase_band(phase) + rank_steps - round(confidence * rank_steps)
```

### Grouping in Claim
```python
queue.claim(
    limit=10,
    phase_field='phase',
    grouping_field='candidate_id'  # All locales of same candidate together
)
```

## Questions?

Refer to `gaps-and-decisions.md` for open questions and design decisions. If unclear on a chapter, check its interdependencies in the chapter file itself under "Coordination Scope".
