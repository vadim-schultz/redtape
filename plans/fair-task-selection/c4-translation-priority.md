---
id: C4
depends_on:
  - C1
  - C2
touches:
  - apps/api/app/features/translation/priority.py
  - apps/api/app/features/translation/source.py
  - tests/features/translation/
execution: chapter-implementer
---

# C4: Update Translation Priority (Candidates)

## Goal

Modify translation task priority calculation to include phase component, ensuring phase-1 tasks always rank above phase-2.

## Acceptance Criteria

- ✅ Priority formula includes phase component (phase-1 items rank 0–99,999, phase-2 items rank 100,000+)
- ✅ Backward compatibility: existing priority logic (confidence ranking) preserved within phase bands
- ✅ All 10 locales of a candidate have adjacent priority indices for grouping
- ✅ Unit tests cover happy path (priority ordering correct) + negative path (old logic didn't have this)
- ✅ Refactor: No duplication between `snapshot_first_priority()` and `first_priority()`

## Scope

**What's in C4:**
- Update `priority.py` functions: `first_priority()`, `retranslation_priority()`
- Update `source.py` to read phase from `fair_selection_state`
- Unit tests for priority calculation
- Integration test: Enqueue candidates, verify priority order

**What's NOT in C4:**
- State transition logic (C3)
- Snapshot-specific changes (C5)
- Queue claim logic changes (C8)

## Implementation Plan

### Slice 1: Read Phase from Database

**Red**: Two tests:

1. **Happy path**: Read phase for a candidate
   - Setup: `FairSelectionState(pipeline='translation', entity_id=candidate_id, phase=2, ...)`
   - Call: `get_phase_for_candidate(candidate_id)` → returns 2
   - Assert: Correct phase read

2. **Negative path**: Missing phase entry returns default
   - Setup: No entry in `fair_selection_state` for candidate_id
   - Call: `get_phase_for_candidate(candidate_id)` → returns 1 (default)
   - Assert: Doesn't crash; assumes phase 1

**Green**: Add helper function:

```python
# apps/api/app/features/translation/source.py

from app.models.fair_selection import FairSelectionState
from sqlalchemy.orm import Session

def get_phase_for_candidate(session: Session, candidate_id: UUID) -> int:
    """Read phase for a candidate; default to phase 1 if not found."""
    state = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == 'translation',
        FairSelectionState.entity_id == candidate_id
    ).first()
    return state.phase if state else 1

def get_phases_for_candidates(session: Session, candidate_ids: List[UUID]) -> Dict[UUID, int]:
    """Read phases for multiple candidates."""
    states = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == 'translation',
        FairSelectionState.entity_id.in_(candidate_ids)
    ).all()
    result = {s.entity_id: s.phase for s in states}
    # Fill in defaults for missing entries
    for cid in candidate_ids:
        if cid not in result:
            result[cid] = 1
    return result
```

**Refactor**: Check for N+1 query issues; use `get_phases_for_candidates()` in batch operations.

### Slice 2: Modify Priority Formula to Include Phase

**Red**: Two tests:

1. **Happy path**: Phase component applied correctly
   - Scenario: Candidate A (confidence=0.9, phase=1) vs. Candidate B (confidence=0.9, phase=2)
   - Calculate: `first_priority(0.9, phase=1)` → should be < `first_priority(0.9, phase=2)`
   - Assert: A's priority is in band 0–99,999; B's is in band 100,000–199,999

2. **Negative path**: Within same phase, confidence order preserved
   - Scenario: Candidate A (confidence=0.9, phase=1) vs. Candidate B (confidence=0.3, phase=1)
   - Calculate: `first_priority(0.9, phase=1)` vs. `first_priority(0.3, phase=1)`
   - Assert: A's priority < B's (high confidence comes first, as before)

**Green**: Update `priority.py`:

```python
# apps/api/app/features/translation/priority.py

FIRST_BASE = 0
RETRANSLATION_BASE = 10_000
UPGRADE_BASE = 20_000

RANK_STEPS = 1000

def _rank(confidence: float) -> int:
    """Convert confidence [0.0, 1.0] to rank [0, 1000]."""
    return 1000 - round(min(max(confidence, 0.0), 1.0) * RANK_STEPS)

def first_priority(confidence: float, phase: int = 1) -> int:
    """
    Calculate priority for a first translation.

    Priority bands by phase:
      phase=1: 0–99,999 (breadth-first)
      phase=2: 100,000–199,999 (depth-first)
      phase=3: 200,000+ (refresh)

    Within phase, ordered by confidence (high first).
    """
    phase_band = (phase - 1) * 100_000  # phase 1→0, 2→100k, 3→200k
    rank = _rank(confidence)
    return phase_band + FIRST_BASE + rank

def retranslation_priority(confidence: float, phase: int = 1) -> int:
    """Calculate priority for a re-translation (stale)."""
    phase_band = (phase - 1) * 100_000
    rank = _rank(confidence)
    return phase_band + RETRANSLATION_BASE + rank

def upgrade_priority(phase: int = 1) -> int:
    """Calculate priority for an Azure upgrade."""
    phase_band = (phase - 1) * 100_000
    return phase_band + UPGRADE_BASE
```

**Refactor**: Check for duplication between `first_priority()` and `retranslation_priority()`. Both have the same phase-band calculation; extract it:

```python
def _phase_band(phase: int) -> int:
    """Convert phase (1–3) to priority band offset."""
    return (phase - 1) * 100_000

def first_priority(confidence: float, phase: int = 1) -> int:
    return _phase_band(phase) + FIRST_BASE + _rank(confidence)

def retranslation_priority(confidence: float, phase: int = 1) -> int:
    return _phase_band(phase) + RETRANSLATION_BASE + _rank(confidence)

def upgrade_priority(phase: int = 1) -> int:
    return _phase_band(phase) + UPGRADE_BASE
```

✅ Extracted `_phase_band()` helper; reduced duplication.

### Slice 3: Update Enqueue Logic to Pass Phase

**Red**: Two tests:

1. **Happy path**: Enqueue passes phase to priority calculation
   - Setup: Candidate with phase=2 in `fair_selection_state`
   - Call: `enqueue_translation(candidate_id, ...)`
   - Assert: Task created with priority in band 100,000–199,999 (phase 2)

2. **Negative path**: Enqueue defaults to phase 1 if not found
   - Setup: Candidate NOT in `fair_selection_state`
   - Call: `enqueue_translation(candidate_id, ...)`
   - Assert: Task created with priority in band 0–99,999 (phase 1)

**Green**: Update `TranslationEnqueuer`:

```python
# apps/api/app/features/translation/enqueue.py

class TranslationEnqueuer:
    def __init__(self, session: Session):
        self.session = session

    def enqueue_many(self, candidate_ids: List[UUID], target_locales: List[str]) -> None:
        """Enqueue translation tasks for candidates."""

        # Read phases for all candidates
        phases = get_phases_for_candidates(self.session, candidate_ids)

        # Read confidences
        confidences = self._confidences_for(candidate_ids)

        for cid in candidate_ids:
            phase = phases.get(cid, 1)
            confidence = confidences.get(cid, 0.0)

            for locale in target_locales:
                # Check if already translated
                existing = self.session.query(TranslationTask).filter(
                    TranslationTask.candidate_id == cid,
                    TranslationTask.locale == locale
                ).first()

                if existing and existing.status == 'COMPLETED':
                    # Already translated; skip or enqueue as retranslation
                    priority = retranslation_priority(confidence, phase)
                    self._upsert_task(cid, locale, priority, is_retranslation=True)
                elif not existing:
                    # New translation
                    priority = first_priority(confidence, phase)
                    self._upsert_task(cid, locale, priority)
                # If PENDING or CLAIMED, leave it alone

    def _upsert_task(self, candidate_id: UUID, locale: str, priority: int, is_retranslation: bool = False) -> None:
        """Create or update task with new priority."""
        # Use ON CONFLICT DO UPDATE to avoid duplicates
        pass
```

**Refactor**: Check if `_upsert_task()` has complex logic; extract if needed.

### Slice 4: Ensure Locale Index for Grouping

**Red**: Two tests:

1. **Happy path**: All locales of same candidate have adjacent priorities
   - Scenario: Candidate (phase=1, confidence=0.9), 10 locales [en, de, fr, ...]
   - Enqueue all 10 tasks
   - Retrieve all 10 tasks; sort by priority
   - Assert: Priorities are `100 + i` for i in 0–9 (adjacent, same phase/confidence, only differ by locale index)

2. **Negative path**: Different candidates don't collide
   - Scenario: 2 candidates (both phase=1, confidence=0.9), 10 locales each
   - Enqueue all 20 tasks
   - Retrieve; sort by priority
   - Assert: Candidate A's tasks are `100–109`, Candidate B's are `110–119` (non-overlapping ranges due to `locale_index`)

**Green**: Ensure locale_index applied:

```python
def first_priority(confidence: float, phase: int = 1, locale_index: int = 0) -> int:
    """Calculate priority; locale_index used as tie-break."""
    phase_band = _phase_band(phase)
    rank = _rank(confidence)
    # Priority uses locale_index for stable ordering within same (phase, rank)
    # This ensures grouping in claim pulls all locales of same candidate together
    return phase_band + rank * 100 + locale_index
```

**Refactor**: Check if locale_index is already tracked; if not, compute it from `LOCALES` list at enqueue time.

### Slice 5: Unit Tests

**Red**: Write tests covering both happy + negative paths

**Green**: Test file:

```python
# tests/features/translation/test_fair_selection_priority.py

def test_phase_one_tasks_always_rank_before_phase_two():
    """Verify phase-1 tasks claim before phase-2 tasks."""
    p1 = first_priority(0.1, phase=1)  # Lowest confidence, phase 1
    p2 = first_priority(0.9, phase=2)  # Highest confidence, phase 2
    assert p1 < p2, f"Phase 1 {p1} should < Phase 2 {p2}"

def test_confidence_ordering_within_phase():
    """Verify confidence still affects priority within same phase."""
    p_high = first_priority(0.9, phase=1)
    p_low = first_priority(0.1, phase=1)
    assert p_high < p_low, f"High confidence {p_high} should < low confidence {p_low}"

def test_locale_index_provides_stable_tiebreak():
    """Verify locale_index ensures adjacent priorities."""
    p0 = first_priority(0.9, phase=1, locale_index=0)
    p1 = first_priority(0.9, phase=1, locale_index=1)
    assert p1 == p0 + 1, f"Locale indices should differ by 1: {p1} vs {p0}"

def test_enqueue_uses_phase_from_database():
    """Verify enqueue reads phase from fair_selection_state."""
    # Setup
    session = db_session()
    candidate_id = uuid4()
    FairSelectionState.create(
        session, pipeline='translation', entity_id=candidate_id, phase=2
    )

    # Enqueue
    enqueuer = TranslationEnqueuer(session)
    enqueuer.enqueue_many([candidate_id], ['en', 'de'])

    # Verify priority band
    tasks = session.query(TranslationTask).filter(
        TranslationTask.candidate_id == candidate_id
    ).all()
    for task in tasks:
        assert 100_000 <= task.priority < 200_000, f"Expected phase-2 priority, got {task.priority}"
```

**Refactor**: Check for duplication with existing priority tests; integrate rather than add new test file.

## Test Output

**After this chapter**:
- Updated `apps/api/app/features/translation/priority.py`
- Updated `apps/api/app/features/translation/source.py`
- Updated `apps/api/app/features/translation/enqueue.py`
- Test file: `tests/features/translation/test_fair_selection_priority.py`

## Gate

✅ Local: `pytest tests/features/translation/test_fair_selection_priority.py` (all 5 slices)
✅ Full: `scripts/ci.sh` (overall lint, type check, existing tests)

## Notes

- Phase passed as optional parameter; defaults to 1 for backward compat
- Enqueue must query `fair_selection_state` per batch; consider caching if many candidates
- Locale index assumes static locale list; if dynamic, adjust at enqueue time
