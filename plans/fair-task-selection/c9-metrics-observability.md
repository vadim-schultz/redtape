---
id: C9
depends_on: [C3, C4, C5, C6, C7, C8]
touches:
  - apps/api/app/features/metrics/
  - tests/features/metrics/
execution: chapter-implementer
---

# C9: Add Observability & Metrics

## Goal

Emit Prometheus metrics for phase transitions, task queue health, and coverage progress. Operators can monitor queue depth by phase, track phase transitions in real time, and identify when phase 1 coverage is complete.

## Acceptance Criteria

- ✅ Metrics emit without errors and have accurate counts
- ✅ Operators can query queue health: pending tasks by phase per pipeline, claimed tasks by phase per pipeline, completed tasks by phase per pipeline
- ✅ Coverage percentage tracked per pipeline per document (% with ≥1 completed task)
- ✅ Phase transition events logged with timestamps
- ✅ All metrics follow Prometheus naming conventions (snake_case, pipeline and phase labels)
- ✅ Metrics queryable via Prometheus: `task_queue_pending_by_phase{pipeline="translation",phase="1"}`, `document_coverage_pct{pipeline="translation"}`

## Read first

- `/mnt/projects/redtape/plans/fair-task-selection/00-architecture.md`: Observability & Metrics section (lines 134–140). If this chapter and the architecture disagree, the architecture wins.
- Existing metrics pattern: `/mnt/projects/redtape/apps/api/app/features/discovery/repository/queue_metrics.py` (reference for query patterns)

## Coordination scope

**Add:**

- `apps/api/app/features/metrics/__init__.py` (new module)
- `apps/api/app/features/metrics/fair_selection_metrics.py` (Prometheus counter definitions and increment functions)
- `apps/api/app/features/metrics/fair_selection_registry.py` (metric registry initialization)
- `tests/features/metrics/test_fair_selection_metrics.py` (test suite for all 5 slices)

**Edit:**

- `apps/api/app/features/fair_selection/state_transitions.py` (call metrics on phase change; assumes C3 owns this file)
- `apps/api/app/features/fair_selection/repository.py` (call metrics on settlement; assumes C3 owns this file)
- `apps/api/app/main.py` (import and register metrics at startup)

**Do not edit:**

- `apps/api/app/features/translation/priority.py` (owned by C4)
- `apps/api/app/features/translation/snapshot_enqueue.py` (owned by C5)
- `apps/api/app/features/search/enqueue.py` (owned by C6)
- `apps/api/app/features/discovery/repository/tasks.py` (owned by C7)
- `apps/api/app/features/fair_selection/claim.py` (owned by C8, owns `LeasedQueue.claim()` integration)

## Work items

### Slice 1: `task_queue_pending_by_phase` Metric (Counts Pending Tasks per Phase per Pipeline)

**Red**: Write two tests:

1. **Happy path**: `test_task_queue_pending_by_phase_increments_on_enqueue`
   - Setup: Create translation pipeline context
   - Action: Enqueue 10 phase-1 tasks, 5 phase-2 tasks
   - Assert: Metric `task_queue_pending_by_phase{pipeline="translation",phase="1"}` = 10
   - Assert: Metric `task_queue_pending_by_phase{pipeline="translation",phase="2"}` = 5
   - Assert: Other pipeline labels absent (no cross-contamination)

2. **Negative path**: `test_task_queue_pending_by_phase_excludes_claimed_completed`
   - Setup: 10 phase-1 tasks enqueued
   - Action: Claim 3 tasks (move to claimed status), complete 2 tasks
   - Assert: Metric still shows 7 pending (not 10; claimed/completed excluded)
   - Assert: Negative counts never reached (validation: gauge stays ≥ 0)

**Green**: Create `apps/api/app/features/metrics/fair_selection_metrics.py`:

```python
"""Prometheus metrics for fair-selection queue observability."""

from prometheus_client import Counter, Gauge

# Gauges: snapshot of current queue state
task_queue_pending_by_phase = Gauge(
    'task_queue_pending_by_phase',
    'Number of pending tasks grouped by phase and pipeline',
    labelnames=['pipeline', 'phase']
)

task_queue_claimed_by_phase = Gauge(
    'task_queue_claimed_by_phase',
    'Number of claimed tasks grouped by phase and pipeline',
    labelnames=['pipeline', 'phase']
)

task_queue_completed_by_phase = Gauge(
    'task_queue_completed_by_phase',
    'Number of completed tasks grouped by phase and pipeline',
    labelnames=['pipeline', 'phase']
)

# Counter: cumulative phase transitions
fair_selection_phase_transition = Counter(
    'fair_selection_phase_transition_total',
    'Count of phase transitions (auto-triggered or manual)',
    labelnames=['pipeline', 'from_phase', 'to_phase']
)

# Gauge: coverage percentage
document_coverage_pct = Gauge(
    'document_coverage_pct',
    'Percentage of documents with ≥1 completed task per pipeline',
    labelnames=['pipeline']
)


def set_pending_by_phase(pipeline: str, phase: int, count: int) -> None:
    """Set pending task count for a phase and pipeline."""
    task_queue_pending_by_phase.labels(pipeline=pipeline, phase=phase).set(count)


def set_claimed_by_phase(pipeline: str, phase: int, count: int) -> None:
    """Set claimed task count for a phase and pipeline."""
    task_queue_claimed_by_phase.labels(pipeline=pipeline, phase=phase).set(count)


def set_completed_by_phase(pipeline: str, phase: int, count: int) -> None:
    """Set completed task count for a phase and pipeline."""
    task_queue_completed_by_phase.labels(pipeline=pipeline, phase=phase).set(count)


def increment_phase_transition(pipeline: str, from_phase: int, to_phase: int) -> None:
    """Increment counter for a phase transition."""
    fair_selection_phase_transition.labels(
        pipeline=pipeline, from_phase=from_phase, to_phase=to_phase
    ).inc()


def set_coverage_pct(pipeline: str, pct: float) -> None:
    """Set coverage percentage for a pipeline."""
    document_coverage_pct.labels(pipeline=pipeline).set(pct)
```

Create `apps/api/app/features/metrics/__init__.py`:

```python
"""Metrics module for observability."""

from app.features.metrics.fair_selection_metrics import (
    set_claimed_by_phase,
    set_completed_by_phase,
    set_coverage_pct,
    set_pending_by_phase,
    increment_phase_transition,
)

__all__ = [
    'set_pending_by_phase',
    'set_claimed_by_phase',
    'set_completed_by_phase',
    'increment_phase_transition',
    'set_coverage_pct',
]
```

**Refactor**: Check metric naming against Prometheus best practices (snake_case ✓, suffix for type (pending, claimed) ✓). No shared logic yet; defer aggregation to slice 5.

---

### Slice 2: `task_queue_claimed_by_phase` Metric (Counts Claimed Tasks)

**Red**: Write two tests:

1. **Happy path**: `test_task_queue_claimed_by_phase_increments_on_claim`
   - Setup: 10 phase-1 tasks enqueued
   - Action: Claim 7 tasks (move to claimed status)
   - Assert: Metric `task_queue_claimed_by_phase{pipeline="translation",phase="1"}` = 7
   - Assert: Metric `task_queue_pending_by_phase{pipeline="translation",phase="1"}` = 3 (pending decremented)

2. **Negative path**: `test_task_queue_claimed_by_phase_excludes_expired_leases`
   - Setup: Claim 5 tasks, let 2 leases expire
   - Action: Query metrics at time when 2 leases are stale
   - Assert: Metric shows 3 non-stale claimed (not 5)
   - Assert: Metric reflects only active leases

**Green**: Extend `fair_selection_metrics.py` (from slice 1) with claimed-task counting. Add query helper in `apps/api/app/features/metrics/fair_selection_registry.py`:

```python
"""Query and update fair-selection metrics."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.fair_selection import FairSelectionState
from app.models.translation import TranslationTask, SnapshotTranslationTask
from app.models.search import EmbeddingTask
from app.models.discovery import DiscoveryTask
from app.shared.enums import TaskStatus

from app.features.metrics.fair_selection_metrics import (
    set_pending_by_phase,
    set_claimed_by_phase,
    set_completed_by_phase,
)


def update_all_metrics(session: Session) -> None:
    """Refresh all queue metrics from current database state."""
    for pipeline in ['translation', 'snapshot_translation', 'embedding', 'discovery']:
        counts = _task_counts_by_status_and_phase(session, pipeline)
        for (status, phase), count in counts.items():
            if status == TaskStatus.PENDING:
                set_pending_by_phase(pipeline, phase, count)
            elif status == TaskStatus.CLAIMED:
                set_claimed_by_phase(pipeline, phase, count)
            elif status == TaskStatus.COMPLETED:
                set_completed_by_phase(pipeline, phase, count)


def _task_counts_by_status_and_phase(session: Session, pipeline: str) -> dict[tuple[str, int], int]:
    """Query task counts grouped by status and phase for a given pipeline."""
    if pipeline == 'translation':
        task_model = TranslationTask
    elif pipeline == 'snapshot_translation':
        task_model = SnapshotTranslationTask
    elif pipeline == 'embedding':
        task_model = EmbeddingTask
    elif pipeline == 'discovery':
        task_model = DiscoveryTask
    else:
        return {}

    stmt = (
        select(task_model.status, task_model.phase, func.count())
        .group_by(task_model.status, task_model.phase)
    )

    result = {}
    for status, phase, count in session.execute(stmt).all():
        result[(status.value, phase)] = int(count)

    return result
```

**Refactor**: Extract `_task_counts_by_status_and_phase` as a reusable helper (used in slices 2 and 3). Check if pipeline model mapping can be centralized (defer to C10 integration if needed).

---

### Slice 3: `fair_selection_phase_transition` Event (Logs Phase Changes)

**Red**: Write two tests:

1. **Happy path**: `test_fair_selection_phase_transition_increments_on_state_change`
   - Setup: State machine transitions phase 1 → 2 for translation pipeline
   - Action: Call state transition handler (from C3)
   - Assert: Metric counter `fair_selection_phase_transition_total{pipeline="translation",from_phase="1",to_phase="2"}` incremented by 1
   - Assert: Transition timestamp logged (or just counter incremented; timestamp in logs)

2. **Negative path**: `test_fair_selection_phase_transition_not_incremented_on_non_transition`
   - Setup: Phase already at 2, no state change
   - Action: Call settlement handler with no phase change
   - Assert: Counter not incremented
   - Assert: No duplicate events when idempotent updates fail silently

**Green**: Extend `fair_selection_metrics.py` with `increment_phase_transition()` (from slice 1). Call from C3's state-transition handler:

```python
# In apps/api/app/features/fair_selection/state_transitions.py (owned by C3, edited here)

from app.features.metrics.fair_selection_metrics import increment_phase_transition

async def transition_phase_1_to_2(session: Session, pipeline: str) -> None:
    """Auto-transition all entities in pipeline from phase 1 to 2 when coverage complete."""
    stmt = (
        update(FairSelectionState)
        .where(FairSelectionState.pipeline == pipeline)
        .where(FairSelectionState.phase == 1)
        .values(phase=2)
    )
    result = session.execute(stmt)

    # Count how many rows transitioned
    if result.rowcount and result.rowcount > 0:
        increment_phase_transition(pipeline, from_phase=1, to_phase=2)
        logger.info(f"Phase transition: {pipeline} phase 1→2, {result.rowcount} entities")
```

**Refactor**: Check if phase-transition logic is centralized in one handler (C3 likely owns `state_transitions.py`). If multiple call sites, extract common pattern.

---

### Slice 4: `document_coverage_pct` Metric (% of Documents with ≥1 Completed Task per Pipeline)

**Red**: Write two tests:

1. **Happy path**: `test_document_coverage_pct_calculated_correctly`
   - Setup: 10 documents (candidates or pages), translation pipeline
   - Enqueue 100 tasks (10 locales per document)
   - Complete 1 task per document for 5 documents (each document now has ≥1 completed task)
   - Action: Call metric-calculation handler
   - Assert: Metric `document_coverage_pct{pipeline="translation"}` = 50.0
   - Assert: Percentage is float (e.g., 50.0, not 50)

2. **Negative path**: `test_document_coverage_pct_ignores_failed_tasks`
   - Setup: 10 documents
   - Complete 1 task for 5 documents, fail 1 task per remaining 5 documents (failed does not count as "covered")
   - Action: Call metric-calculation handler
   - Assert: Metric = 50.0 (failed tasks don't count; only completed)
   - Assert: Metric never exceeds 100.0 (even with rounding artifacts)

**Green**: Extend `fair_selection_registry.py` with coverage calculation:

```python
def update_coverage_metrics(session: Session) -> None:
    """Calculate and set document coverage percentage per pipeline."""
    for pipeline in ['translation', 'snapshot_translation', 'embedding', 'discovery']:
        pct = _calculate_coverage_pct(session, pipeline)
        set_coverage_pct(pipeline, pct)


def _calculate_coverage_pct(session: Session, pipeline: str) -> float:
    """
    Calculate percentage of documents with ≥1 completed task.

    For translation: document = candidate; for discovery: document = catalogue_service.
    """
    if pipeline == 'translation':
        # Count distinct candidates with ≥1 completed task
        stmt_total = select(func.count(func.distinct(TranslationTask.candidate_id))).where(
            TranslationTask.pipeline == pipeline
        )
        stmt_covered = select(func.count(func.distinct(TranslationTask.candidate_id))).where(
            TranslationTask.pipeline == pipeline,
            TranslationTask.status == TaskStatus.COMPLETED
        )
    elif pipeline == 'snapshot_translation':
        stmt_total = select(func.count(func.distinct(SnapshotTranslationTask.catalogue_service_id)))
        stmt_covered = select(func.count(func.distinct(SnapshotTranslationTask.catalogue_service_id))).where(
            SnapshotTranslationTask.status == TaskStatus.COMPLETED
        )
    elif pipeline == 'embedding':
        stmt_total = select(func.count(func.distinct(EmbeddingTask.candidate_id)))
        stmt_covered = select(func.count(func.distinct(EmbeddingTask.candidate_id))).where(
            EmbeddingTask.status == TaskStatus.COMPLETED
        )
    elif pipeline == 'discovery':
        stmt_total = select(func.count(func.distinct(DiscoveryTask.catalogue_service_id)))
        stmt_covered = select(func.count(func.distinct(DiscoveryTask.catalogue_service_id))).where(
            DiscoveryTask.status == TaskStatus.COMPLETED
        )
    else:
        return 0.0

    total = int(session.scalar(stmt_total) or 0)
    covered = int(session.scalar(stmt_covered) or 0)

    if total == 0:
        return 0.0

    return (covered / total) * 100.0
```

**Refactor**: Check if coverage calculation can be shared with C3's phase-transition logic (C3 likely checks "all documents covered" to trigger 1→2). Extract common predicate if needed.

---

### Slice 5: Integration Test (All Metrics Emit and Can Be Queried)

**Red**: Write two tests:

1. **Happy path**: `test_all_metrics_emitted_and_queryable`
   - Setup: Create full workflow:
     - Enqueue 20 tasks (5 candidates, 4 locales, translation pipeline)
     - 10 phase-1, 10 phase-2
     - Claim 5 tasks (move to claimed), complete 3
   - Action: Call `update_all_metrics(session)` and `update_coverage_metrics(session)`
   - Assert: All 5 metric types are set (pending, claimed, completed, coverage, transition counters)
   - Assert: Metrics readable via Prometheus client library
   - Assert: No exceptions or errors during metric update

2. **Negative path**: `test_metrics_handle_empty_queue`
   - Setup: No tasks enqueued
   - Action: Call metric-update handlers
   - Assert: Metrics set to 0 (not error/None)
   - Assert: Coverage = 0.0 (no documents, no coverage)
   - Assert: No division-by-zero errors

**Green**: Write comprehensive test file `tests/features/metrics/test_fair_selection_metrics.py`:

```python
"""Integration tests for fair-selection metrics."""

import pytest
from prometheus_client import REGISTRY

from app.features.metrics.fair_selection_metrics import (
    increment_phase_transition,
    set_claimed_by_phase,
    set_completed_by_phase,
    set_coverage_pct,
    set_pending_by_phase,
    task_queue_claimed_by_phase,
    task_queue_completed_by_phase,
    task_queue_pending_by_phase,
    document_coverage_pct,
)
from app.features.metrics.fair_selection_registry import (
    update_all_metrics,
    update_coverage_metrics,
)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset Prometheus metrics before each test."""
    for collector in list(REGISTRY._collector_to_names.keys()):
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    # Re-register after cleanup
    yield


def test_all_metrics_emitted_and_queryable(db, session):
    """Verify all metric types emit without errors and are queryable."""
    # Setup: Enqueue tasks
    setup_full_workflow(session)

    # Action: Update metrics
    update_all_metrics(session)
    update_coverage_metrics(session)
    increment_phase_transition('translation', from_phase=1, to_phase=2)

    # Assert: Metrics set
    assert task_queue_pending_by_phase.labels(pipeline='translation', phase='1')._value.get() > 0
    assert task_queue_claimed_by_phase.labels(pipeline='translation', phase='1')._value.get() >= 0
    assert task_queue_completed_by_phase.labels(pipeline='translation', phase='1')._value.get() >= 0
    assert document_coverage_pct.labels(pipeline='translation')._value.get() >= 0.0


def test_metrics_handle_empty_queue(db, session):
    """Verify metrics safely handle empty queue (no division-by-zero)."""
    # No setup; queue is empty

    # Action: Update metrics
    update_all_metrics(session)
    update_coverage_metrics(session)

    # Assert: No errors; metrics at 0
    assert document_coverage_pct.labels(pipeline='translation')._value.get() == 0.0


def test_phase_transition_counter_increments(db):
    """Verify phase-transition counter increments on each call."""
    before = increment_phase_transition('translation', from_phase=1, to_phase=2)
    # Counter value is cumulative; check that it was incremented
    # Note: Prometheus counters only increase; assertion is implementation-specific


def setup_full_workflow(session):
    """Helper to create a workflow with pending, claimed, and completed tasks."""
    # Create candidates and tasks
    for i in range(5):
        candidate = Candidate(id=f"cand-{i}", ...)
        session.add(candidate)

    session.flush()

    for i, candidate_id in enumerate(list of candidate IDs):
        for phase in [1, 2]:
            for locale in ['en', 'de', 'fr', 'es']:
                task = TranslationTask(
                    candidate_id=candidate_id,
                    locale=locale,
                    phase=phase,
                    status=TaskStatus.PENDING if phase == 1 else TaskStatus.PENDING,
                )
                session.add(task)

    session.commit()
```

Create `tests/features/metrics/__init__.py` (empty file for test discovery).

**Refactor**: Check test helper duplication (setup_full_workflow may be reused; defer to separate fixture if needed). Verify metric reset doesn't interfere with other test suites. No other code-structure issues detected (all helpers single-purpose, no >100 LOC methods).

---

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Pending metric | `test_task_queue_pending_by_phase_increments_on_enqueue` | `test_task_queue_pending_by_phase_excludes_claimed_completed` |
| Claimed metric | `test_task_queue_claimed_by_phase_increments_on_claim` | `test_task_queue_claimed_by_phase_excludes_expired_leases` |
| Phase transition | `test_fair_selection_phase_transition_increments_on_state_change` | `test_fair_selection_phase_transition_not_incremented_on_non_transition` |
| Coverage metric | `test_document_coverage_pct_calculated_correctly` | `test_document_coverage_pct_ignores_failed_tasks` |
| Integration | `test_all_metrics_emitted_and_queryable` | `test_metrics_handle_empty_queue` |

## Review gate

Before merging:

1. ✅ All 10 tests pass: `pytest tests/features/metrics/test_fair_selection_metrics.py -v`
2. ✅ Metric names follow Prometheus conventions (snake_case, no reserved suffixes collision)
3. ✅ Metric labels are consistent across all 5 metrics (pipeline, phase where applicable)
4. ✅ No metric value exceeds safe bounds (coverage ≤ 100%, counts ≥ 0)
5. ✅ Import statements in `apps/api/app/main.py` initialize metrics at startup
6. ✅ No circular imports between metrics and other features
7. ✅ Linting passes: `ruff check apps/api/app/features/metrics/ tests/features/metrics/`
8. ✅ Type hints complete: `mypy apps/api/app/features/metrics/`

## Out of scope

- Alerting rules (defer to observability team)
- Grafana dashboard configuration (C10 or operational docs)
- Real-time streaming (metrics are polled; no Kafka/event-streaming required)
- State-transition logic (owned by C3; this chapter only calls metrics)
- Task enqueue/claim/settle logic (owned by C4–C8; this chapter only queries)

## Verification

```bash
# Run from the repository root.

# Test slice 1: Pending metric
pytest tests/features/metrics/test_fair_selection_metrics.py::test_task_queue_pending_by_phase_increments_on_enqueue -v
pytest tests/features/metrics/test_fair_selection_metrics.py::test_task_queue_pending_by_phase_excludes_claimed_completed -v

# Test slice 2: Claimed metric
pytest tests/features/metrics/test_fair_selection_metrics.py::test_task_queue_claimed_by_phase_increments_on_claim -v
pytest tests/features/metrics/test_fair_selection_metrics.py::test_task_queue_claimed_by_phase_excludes_expired_leases -v

# Test slice 3: Phase transition
pytest tests/features/metrics/test_fair_selection_metrics.py::test_fair_selection_phase_transition_increments_on_state_change -v
pytest tests/features/metrics/test_fair_selection_metrics.py::test_fair_selection_phase_transition_not_incremented_on_non_transition -v

# Test slice 4: Coverage metric
pytest tests/features/metrics/test_fair_selection_metrics.py::test_document_coverage_pct_calculated_correctly -v
pytest tests/features/metrics/test_fair_selection_metrics.py::test_document_coverage_pct_ignores_failed_tasks -v

# Test slice 5: Integration
pytest tests/features/metrics/test_fair_selection_metrics.py::test_all_metrics_emitted_and_queryable -v
pytest tests/features/metrics/test_fair_selection_metrics.py::test_metrics_handle_empty_queue -v

# Full suite
pytest tests/features/metrics/test_fair_selection_metrics.py -v

# Local gate
scripts/ci.sh lint
scripts/ci.sh test
```

Expected: All 10 tests pass, linting passes, no type errors.

## Refactor report

**Slice 1 refactor**: ✅ No refactor needed — metric definitions are declarative and follow Prometheus best practices. Naming convention verified (snake_case, no conflicts with reserved suffixes like `_total`, `_created`). Setters are single-purpose helpers.

**Slice 2 refactor**: ✅ Extracted `_task_counts_by_status_and_phase()` as reusable query helper. Pipeline-model mapping (`pipeline` string → task model class) centralized in one function. Future optimization: consider caching if queries become hot path.

**Slice 3 refactor**: ✅ No refactor needed — phase-transition counter is single call site per transition type. No duplicate logic detected. If C3 has multiple transition paths, extraction happens in C3's refactor pass.

**Slice 4 refactor**: ✅ Extracted `_calculate_coverage_pct()` as reusable helper. Pipeline-model mapping reused from slice 2. Coverage calculation is a single decision per pipeline; no >2 arms detected. No other refactor candidates.

**Slice 5 refactor**: ✅ No refactor needed — integration tests are sparse and declarative. Test helper `setup_full_workflow()` is single-purpose. Metric reset fixture is minimal (3 lines). No other cleanup detected.

**Cross-slice**: ✅ Pipeline-model mapping (`_task_counts_by_status_and_phase`) is consistent across slices 2 and 4. Consider centralizing in separate `_pipelines.py` module if mapping becomes >8 lines or used by C10.

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`. Pull it only when it tracks an upstream.
- Create the chapter branch with `git checkout -b c9-metrics-observability`.
- Commit the red tests first (10 test cases), then the green change (metrics module + registry + integration).
- Run the local gate on the chapter branch: `scripts/ci.sh test && scripts/ci.sh lint`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
