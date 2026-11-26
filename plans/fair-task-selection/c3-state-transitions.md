---
id: C3
depends_on: [C2]
touches:
  - apps/api/app/features/fair_selection/
  - apps/api/app/models/
  - tests/
execution: chapter-implementer
---

# C3: Implement State Transition Logic

**Depends on:** C2 · **Architecture:** 00-architecture.md (State Transitions section) · **Rollout:** 01-rollout.md

## Goal

Implement the state-transition engine that automatically advances documents from phase 1 (breadth-first coverage) to phase 2 (depth-first completion) when coverage criteria are met, with periodic audits and manual overrides.

## Read first

- **00-architecture.md**: "State Transitions" (auto-transition rules, manual override); "Data Model Changes" (fair_selection_state table, phase columns); "Observability & Metrics" (what to measure).
- **01-rollout.md**: C3 is serial-dependent on C2 (schema); feeds C4–C7 (which read phase state via calls to C3 functions).

## Coordination scope

**Add:**

- `apps/api/app/features/fair_selection/__init__.py`
- `apps/api/app/features/fair_selection/state_machine.py` (core logic: transitions, coverage tracking)
- `apps/api/app/features/fair_selection/audit.py` (periodic audit job)
- `tests/features/fair_selection/test_state_transitions.py` (all slices)

**Edit:**

- `apps/api/app/models/fair_selection.py` (create or update with FairSelectionState ORM model; C2 migration handles schema)

**Do not edit:**

- `apps/api/app/features/translation/` (C4–C5 edit priority calculation; C3 provides state helpers only)
- `apps/api/app/features/search/` (C6, C8 edit embedding & queue logic)
- `apps/api/app/features/discovery/` (C7 edits discovery priority)

## Work items

### Slice 1: `check_phase_one_complete()` Function

**Red**: Two tests:

1. **Happy path** (`test_check_phase_one_complete_all_done`): All documents in catalogue have ≥1 completed task per pipeline
   - Setup: 5 candidates in DB, translation pipeline active
   - Create completed translation tasks: 1 per candidate (at least one task COMPLETED per candidate)
   - Call: `check_phase_one_complete('translation')`
   - Assert: Returns `True`

2. **Negative path** (`test_check_phase_one_complete_partial`): Not all documents have completed tasks
   - Setup: 5 candidates in DB
   - Create completed tasks for only 3 candidates
   - Call: `check_phase_one_complete('translation')`
   - Assert: Returns `False`

**Green**: Implement function in `state_machine.py`:

```python
def check_phase_one_complete(pipeline: str) -> bool:
    """
    Check if all documents in the catalogue have ≥1 completed task per pipeline.

    Args:
        pipeline: Name of pipeline ('translation', 'embedding', 'discovery')

    Returns:
        True if all documents have ≥1 completed task; False otherwise.
    """
    # Query: for each entity_id in fair_selection_state WHERE pipeline=X,
    # check if there is at least one completed task in the corresponding task table
    # Return True only if the set of entities with ≥1 completed task
    # equals the set of all entities for that pipeline

    from app.models import (
        FairSelectionState, TranslationTask, EmbeddingTask,
        DiscoveryTask, SnapshotTranslationTask
    )
    from sqlalchemy import func

    if pipeline == 'translation':
        task_model = TranslationTask
        entity_col = TranslationTask.candidate_id
    elif pipeline == 'embedding':
        task_model = EmbeddingTask
        entity_col = EmbeddingTask.candidate_id
    elif pipeline == 'discovery':
        task_model = DiscoveryTask
        entity_col = DiscoveryTask.catalogue_service_id
    elif pipeline == 'translation_snapshot':
        task_model = SnapshotTranslationTask
        entity_col = SnapshotTranslationTask.catalogue_service_id
    else:
        raise ValueError(f"Unknown pipeline: {pipeline}")

    # Count total unique entities tracked for this pipeline
    total_entities = db.session.query(
        func.count(func.distinct(FairSelectionState.entity_id))
    ).filter(
        FairSelectionState.pipeline == pipeline
    ).scalar() or 0

    if total_entities == 0:
        return True  # No entities = vacuously true (or design decision: return False?)

    # Count unique entities with ≥1 completed task
    completed_entities = db.session.query(
        func.count(func.distinct(entity_col))
    ).filter(
        task_model.status == 'COMPLETED'
    ).scalar() or 0

    return completed_entities >= total_entities
```

**Refactor**: Query optimization: consider a single query using LEFT JOIN or subquery instead of two sequential queries. Measure if the two-query approach is clearer for maintenance.

### Slice 2: `transition_phase()` Function with State Machine

**Red**: Two tests:

1. **Happy path** (`test_transition_phase_one_to_two`): Phase 1 → 2 transition succeeds when all docs complete
   - Setup: 3 candidates, all with ≥1 completed translation task
   - Setup state: All candidates in `fair_selection_state` with phase=1
   - Call: `transition_phase('translation', from_phase=1, to_phase=2)`
   - Assert: All candidates now have phase=2 in `fair_selection_state`
   - Assert: Returns count of updated rows (3)

2. **Negative path** (`test_transition_phase_condition_not_met`): Transition blocked if coverage incomplete
   - Setup: 3 candidates, only 1 has completed task
   - Setup state: All in phase=1
   - Call: `transition_phase('translation', from_phase=1, to_phase=2)`
   - Assert: No rows updated (phase remains 1 for all)
   - Assert: Returns count of updated rows (0)
   - Assert: Does not raise exception (graceful fail)

**Green**: Implement state machine in `state_machine.py`:

```python
def transition_phase(
    pipeline: str,
    from_phase: int,
    to_phase: int,
) -> int:
    """
    Advance all entities in a pipeline from one phase to another if conditions are met.

    **Phase 1 → 2**: Triggered when all entities have ≥1 completed task.
    **Phase 2 → 3**: Triggered when all phase 2 tasks are completed.
    **Phase 3 → 1** (loop): If no phase 3 items remain after all phase 2 done.

    Args:
        pipeline: Pipeline name ('translation', 'embedding', 'discovery')
        from_phase: Current phase (1, 2, or 3)
        to_phase: Target phase (1, 2, or 3)

    Returns:
        Number of rows updated.

    Raises:
        ValueError: Invalid phase transition or pipeline.
    """
    # Validate transition
    valid_transitions = {
        (1, 2): "breadth_first_complete",
        (2, 3): "depth_first_complete",
        (3, 1): "refresh_cycle_reset",
    }
    if (from_phase, to_phase) not in valid_transitions:
        raise ValueError(f"Invalid transition: phase {from_phase} → {to_phase}")

    # Check if transition condition is met
    if from_phase == 1 and to_phase == 2:
        if not check_phase_one_complete(pipeline):
            return 0  # Condition not met; no update
    elif from_phase == 2 and to_phase == 3:
        if not _check_phase_two_complete(pipeline):
            return 0
    elif from_phase == 3 and to_phase == 1:
        if _check_phase_three_exists(pipeline):
            # Phase 3 items exist; do not loop yet
            return 0

    # Perform transition: update all entities in from_phase to to_phase
    from app.models import FairSelectionState

    updated = db.session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == pipeline,
        FairSelectionState.phase == from_phase,
    ).update(
        {FairSelectionState.phase: to_phase, FairSelectionState.updated_at: func.now()},
        synchronize_session=False
    )
    db.session.commit()

    return updated
```

**Refactor**: Extract the three condition-check helpers (`_check_phase_two_complete()`, `_check_phase_three_exists()`) to separate functions for testability and clarity. Keep the main `transition_phase()` function to pure orchestration (check → update → return count).

### Slice 3: Coverage Audit Job (`audit_fair_selection_state()`)

**Red**: Two tests:

1. **Happy path** (`test_audit_detects_and_fixes_coverage_drift`): Audit corrects stale phase state
   - Setup: 5 candidates with mixed completed tasks; `fair_selection_state` has incorrect phase values (some phase=1 when they should be phase=2)
   - Call: `audit_fair_selection_state(pipeline='translation')`
   - Assert: Returns audit report with drift count (how many corrected)
   - Assert: DB now has correct phase values based on actual completed tasks
   - Assert: `coverage_bitmap` updated to reflect completed task types

2. **Negative path** (`test_audit_no_drift_no_changes`): Audit succeeds when state is consistent
   - Setup: State is already correct (phase matches coverage)
   - Call: `audit_fair_selection_state(pipeline='translation')`
   - Assert: Returns report with drift_count=0
   - Assert: No rows modified

**Green**: Implement audit job in `audit.py`:

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class AuditReport:
    pipeline: str
    entities_checked: int
    drift_detected: int
    corrected: int
    errors: list[str]

def audit_fair_selection_state(pipeline: str) -> AuditReport:
    """
    Audit and repair fair_selection_state consistency.

    Recomputes phase and coverage_bitmap for all entities in the pipeline
    based on actual completed tasks. Corrects any drift between tracking
    table and reality.

    Args:
        pipeline: Pipeline name to audit.

    Returns:
        AuditReport with counts and any errors encountered.
    """
    from app.models import FairSelectionState

    report = AuditReport(
        pipeline=pipeline,
        entities_checked=0,
        drift_detected=0,
        corrected=0,
        errors=[],
    )

    # For each entity in fair_selection_state for this pipeline:
    entities = db.session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == pipeline
    ).all()

    for entity in entities:
        report.entities_checked += 1

        try:
            # Compute expected phase and coverage based on completed tasks
            expected_phase, coverage_bitmap = _compute_expected_state(
                pipeline, entity.entity_id
            )

            # Compare with current
            if (entity.phase != expected_phase or
                entity.coverage_bitmap != coverage_bitmap):
                report.drift_detected += 1
                entity.phase = expected_phase
                entity.coverage_bitmap = coverage_bitmap
                entity.updated_at = func.now()
                report.corrected += 1
        except Exception as e:
            report.errors.append(f"Entity {entity.entity_id}: {str(e)}")

    db.session.commit()
    return report
```

**Refactor**: Extract `_compute_expected_state()` as a testable helper. Keep the audit function focused on iteration and reporting.

### Slice 4: Integration: Settlement Hook Calls Transition Logic

**Red**: Two tests:

1. **Happy path** (`test_settlement_hook_triggers_phase_transition`): After settlement completes task, transition logic is called
   - Setup: Enqueue a settlement with candidate that completes final phase-1 coverage
   - Trigger settlement logic (or mock the settlement completion event)
   - Assert: Phase transition logic was called (verify via spy/mock on `transition_phase()`)
   - Assert: Resulting state reflects new phase

2. **Negative path** (`test_settlement_does_not_transition_if_incomplete`): Settlement does not force transition when condition unmet
   - Setup: Settlement completes a task, but coverage is still partial
   - Trigger settlement
   - Assert: `transition_phase()` returns 0 (no change)
   - Assert: Phase remains 1

**Green**: Add settlement hook integration in `state_machine.py`:

```python
def on_task_settled(
    pipeline: str,
    entity_id: UUID,
    task_status: str,  # 'COMPLETED', 'FAILED', etc.
) -> None:
    """
    Called when a task is settled (completed or failed).

    Checks if this settlement allows a phase transition, and triggers
    automatic advancement if criteria are met.

    Args:
        pipeline: Pipeline that settled the task.
        entity_id: Candidate or catalogue_service_id.
        task_status: Final status of the task.
    """
    if task_status != 'COMPLETED':
        return  # Only phase transitions on completion

    # Update coverage bitmap for this entity
    update_coverage_bitmap(pipeline, entity_id, task_status)

    # Attempt phase 1 → 2 transition
    transition_phase(pipeline, from_phase=1, to_phase=2)

    # Note: Phase 2 → 3 may happen during periodic audit, not on every task
```

**Refactor**: Check if the settlement event is already being published elsewhere (e.g., in a task repository or worker). Avoid duplicate calls by routing all settlement events through one handler.

### Slice 5: Metrics for Transitions (Count, Timing, Failures)

**Red**: Two tests:

1. **Happy path** (`test_transition_metrics_recorded_on_success`): Transition metrics are emitted
   - Setup: Trigger a phase 1 → 2 transition
   - Capture metrics emitted (or query metrics DB)
   - Assert: Metric `fair_selection_phase_transition_count` incremented with labels (pipeline='translation', from_phase=1, to_phase=2)
   - Assert: Metric `fair_selection_phase_transition_duration_seconds` recorded (non-zero)

2. **Negative path** (`test_transition_metrics_recorded_on_condition_failure`): Metrics track non-transitions
   - Setup: Attempt phase 1 → 2 transition when condition not met
   - Capture metrics
   - Assert: Metric `fair_selection_phase_transition_blocked_total` incremented with reason (e.g., reason='incomplete_coverage')

**Green**: Add metrics collection in `state_machine.py`:

```python
from prometheus_client import Counter, Histogram
import time

phase_transition_counter = Counter(
    'fair_selection_phase_transition_total',
    'Count of phase transitions completed',
    ['pipeline', 'from_phase', 'to_phase']
)

phase_transition_duration = Histogram(
    'fair_selection_phase_transition_duration_seconds',
    'Duration of phase transition operation',
    ['pipeline']
)

phase_transition_blocked = Counter(
    'fair_selection_phase_transition_blocked_total',
    'Count of phase transitions blocked due to unmet conditions',
    ['pipeline', 'from_phase', 'to_phase', 'reason']
)

def transition_phase(
    pipeline: str,
    from_phase: int,
    to_phase: int,
) -> int:
    """State machine transition with metrics."""

    start = time.time()

    # Check condition...
    if from_phase == 1 and to_phase == 2:
        if not check_phase_one_complete(pipeline):
            phase_transition_blocked.labels(
                pipeline=pipeline,
                from_phase=from_phase,
                to_phase=to_phase,
                reason='incomplete_coverage'
            ).inc()
            return 0

    # Perform update...
    updated = db.session.query(...).update(...)

    # Record metrics
    duration = time.time() - start
    phase_transition_counter.labels(
        pipeline=pipeline,
        from_phase=from_phase,
        to_phase=to_phase
    ).inc()
    phase_transition_duration.labels(pipeline=pipeline).observe(duration)

    return updated
```

**Refactor**: Wrap metrics collection in a decorator or context manager to avoid duplication across transition functions and audit.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Coverage check | `test_check_phase_one_complete_all_done` | `test_check_phase_one_complete_partial` |
| Phase transition | `test_transition_phase_one_to_two` | `test_transition_phase_condition_not_met` |
| Coverage audit | `test_audit_detects_and_fixes_coverage_drift` | `test_audit_no_drift_no_changes` |
| Settlement hook | `test_settlement_hook_triggers_phase_transition` | `test_settlement_does_not_transition_if_incomplete` |
| Metrics | `test_transition_metrics_recorded_on_success` | `test_transition_metrics_recorded_on_condition_failure` |

## Review gate

✅ **Local**: Run narrow test suite for C3 (all slices):
```bash
pytest tests/features/fair_selection/test_state_transitions.py -v
```

Expected: All 10 tests pass (5 slices × 2 tests each). Coverage: `state_machine.py` and `audit.py` >90%.

✅ **Full**: Run formatter and type checker on new module:
```bash
ruff check apps/api/app/features/fair_selection/
ruff format --check apps/api/app/features/fair_selection/
mypy apps/api/app/features/fair_selection/
```

Expected: No linting or type errors. Docstrings complete (D100, D101, D102, D103 rules pass).

✅ **Integration readiness**: Verify no import errors from C4–C7:
```bash
python -c "from app.features.fair_selection.state_machine import transition_phase; print('Import OK')"
```

Expected: Imports succeed; no missing dependencies.

## Out of scope

- **C4–C5**: Translation priority calculation (calls `transition_phase()` as a helper, but does not change state machine logic)
- **C6**: Embedding priority (same as C4–C5)
- **C7**: Discovery task selection (same as C4–C5)
- **C8**: LeasedQueue integration (uses phase state from C3; C3 does not modify queue)
- **C9**: Observability (C3 emits metrics; C9 aggregates and dashboards them)

## Verification

Run from the repository root.

```bash
# 1. Run all C3 tests (all 5 slices, 10 tests total)
pytest tests/features/fair_selection/test_state_transitions.py -v

# 2. Verify imports work (C4–C7 can import and call C3 functions)
python -c "from app.features.fair_selection.state_machine import transition_phase, check_phase_one_complete; print('OK')"
python -c "from app.features.fair_selection.audit import audit_fair_selection_state; print('OK')"

# 3. Check coverage
pytest tests/features/fair_selection/test_state_transitions.py --cov=apps/api/app/features/fair_selection --cov-report=term-missing

# 4. Lint and format
ruff check apps/api/app/features/fair_selection/
ruff format --check apps/api/app/features/fair_selection/

# 5. Type checking
mypy apps/api/app/features/fair_selection/

# 6. Full suite (after C2 integration)
scripts/ci.sh
```

Expected:
- All 10 C3 tests pass
- Imports succeed
- Coverage ≥90% for `state_machine.py` and `audit.py`
- No linting, formatting, or type errors
- Full suite (`scripts/ci.sh`) exits 0

## Refactor report

**Slice 1**: Extract `check_phase_one_complete()` from transition logic; keep it pure (no side effects). No refactor needed in this pass — function is 15 LOC with single concern (coverage check).

**Slice 2**: Extracted three condition-check helpers (`_check_phase_two_complete()`, `_check_phase_three_exists()`) from main `transition_phase()` function. Main function is now 10 LOC (orchestration only: validate → check → update → return). Each helper is 5–8 LOC. Result: Improved testability and readability.

**Slice 3**: Extracted `_compute_expected_state()` from audit loop. `audit_fair_selection_state()` now 12 LOC (iteration, error handling, reporting). `_compute_expected_state()` is 8 LOC (pure computation). Result: Audit function is clearer; state computation can be unit-tested independently.

**Slice 4**: Settlement hook (`on_task_settled()`) is 10 LOC (guard clause + two calls + coverage update). Single concern: react to settlement event. No pre-existing branches; refactor not needed.

**Slice 5**: Metrics wrapped in context manager or decorator (defer if complexity <3 lines per transition point). Currently 5 lines of metric collection per transition. Refactor: Create a `@measure_transition_duration` decorator if more than two transition points use the same pattern. For now, inline metrics with clear labels; revisit if threshold exceeded.

Overall audit of `state_machine.py` (expected ~80 LOC after all slices):
- ✅ Single concern per function (coverage check, state transition, metrics)
- ✅ No pre-existing branches requiring extraction
- ✅ One level of nesting (guard clauses in `transition_phase()`; inner helpers extracted)
- ✅ Docstrings present; types strict
- ✅ <100 LOC per file; no splitting needed

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`. Pull it only when it tracks an upstream.
- Create the chapter branch with `git checkout -b c3-state-transitions`.
- **Commit 1**: Red tests (all 10 test cases in `test_state_transitions.py`). Verify tests fail for the right reason (function not yet implemented).
- **Commit 2**: Green implementation (`state_machine.py`, `audit.py` with all 5 slices complete). Verify all 10 tests pass.
- **Commit 3**: Refactor pass (extract helpers, optimize queries, audit code structure per refactor-step.mdc). Re-run tests after each extraction; stay green.
- Run the local gate on the chapter branch: `pytest tests/features/fair_selection/test_state_transitions.py && ruff check apps/api/app/features/fair_selection/`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
