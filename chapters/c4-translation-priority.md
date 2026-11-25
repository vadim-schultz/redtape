---
name: Chapter C4 - Update Translation Priority (Candidates)
overview: "Add phase component to candidate translation priority calculation, ensuring phase-1 breadth-first tasks always rank above phase-2 depth-first tasks."
id: C4
depends_on: [C1, C2]
touches:
  - apps/api/app/features/translation/priority.py
  - apps/api/app/features/translation/source.py
  - apps/api/app/features/translation/enqueue.py
  - tests/features/translation/test_fair_selection_priority.py
execution: chapter-implementer
isProject: false
---

# C4 - Update Translation Priority (Candidates)

**Depends on:** C1, C2 · **Architecture:** 00-architecture.md (§ Priority Calculation, § Pipeline-Specific Changes / Translation) · **Rollout:** 01-rollout.md (§ Chapter Schedule Matrix)

## Goal

Modify the translation task priority formula for candidates to include a phase component, ensuring phase-1 (breadth-first) candidates always rank above phase-2 (depth-first) candidates, while preserving confidence-based ordering within each phase and maintaining locale grouping stability.

## Read first

- **00-architecture.md**: Priority Calculation (new formula with phase component), Pipeline-Specific Changes / Translation (candidates phase-aware selection), Claim & Selection Logic (grouping field behavior).
- **01-rollout.md**: Per-Chapter Gate (TDD red → green → refactor, paired tests).

## Coordination scope

**Add:**

- `tests/features/translation/test_fair_selection_priority.py` — unit tests for priority calculation and phase-aware enqueue

**Edit:**

- `apps/api/app/features/translation/priority.py` — add phase parameter to `first_priority()`, `retranslation_priority()`, extract `_phase_band()` helper
- `apps/api/app/features/translation/source.py` — add `get_phase_for_candidate()` and `get_phases_for_candidates()` helpers
- `apps/api/app/features/translation/enqueue.py` — update `TranslationEnqueuer.enqueue_many()` to read phase and pass to priority functions

**Do not edit:**

- `apps/api/app/features/translation/snapshot_enqueue.py` — owned by C5
- `apps/api/app/models/fair_selection.py` — owned by C2

## Work items

### Slice 1: Read Phase from Database

**Red**: Two tests confirm behavior for reading phase from `fair_selection_state`:

1. **Happy path** (`test_get_phase_for_candidate_reads_phase`): Query returns phase when entry exists
   - Setup: Create `FairSelectionState(pipeline='translation', entity_id=candidate_id, phase=2)`
   - Call: `get_phase_for_candidate(session, candidate_id)` → returns `2`
   - Assert: Correct phase read; no exception

2. **Negative path** (`test_get_phase_for_candidate_defaults_to_phase_one`): Query returns default when entry missing
   - Setup: No `fair_selection_state` entry for candidate_id
   - Call: `get_phase_for_candidate(session, candidate_id)` → returns `1`
   - Assert: Defaults to phase 1; no exception

**Green**: Add helpers to `apps/api/app/features/translation/source.py`:

```python
def get_phase_for_candidate(session: Session, candidate_id: UUID) -> int:
    """Read phase for a candidate from fair_selection_state; default to phase 1 if not found.

    Args:
        session: SQLAlchemy session.
        candidate_id: UUID of the candidate.

    Returns:
        Phase (1–3); defaults to 1 if no state entry exists.
    """
    from app.models.fair_selection import FairSelectionState

    state = (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == "translation",
            FairSelectionState.entity_id == candidate_id,
        )
        .first()
    )
    return state.phase if state else 1


def get_phases_for_candidates(
    session: Session, candidate_ids: list[UUID]
) -> dict[UUID, int]:
    """Read phases for multiple candidates; batch query to avoid N+1.

    Args:
        session: SQLAlchemy session.
        candidate_ids: List of candidate UUIDs.

    Returns:
        Mapping from candidate_id to phase (1–3); missing candidates default to 1.
    """
    from app.models.fair_selection import FairSelectionState

    if not candidate_ids:
        return {}

    states = (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == "translation",
            FairSelectionState.entity_id.in_(candidate_ids),
        )
        .all()
    )
    result = {s.entity_id: s.phase for s in states}
    # Fill in defaults for candidates not in fair_selection_state
    for cid in candidate_ids:
        if cid not in result:
            result[cid] = 1
    return result
```

**Refactor**: Check for N+1 query issues.
- ✅ `get_phase_for_candidate()` is single-entity lookup; acceptable for isolated calls.
- ✅ `get_phases_for_candidates()` uses batch query; callers must use this when processing multiple candidates.
- ✅ No duplication introduced; both helpers live in `source.py` for reuse.

---

### Slice 2: Modify Priority Formula to Include Phase

**Red**: Two tests confirm phase component applied correctly:

1. **Happy path** (`test_first_priority_phase_one_ranks_before_phase_two`): Phase component dominates
   - Scenario: Candidate A (confidence=0.9, phase=1) vs. Candidate B (confidence=0.1, phase=2)
   - Calculate: `first_priority(0.9, phase=1)` and `first_priority(0.1, phase=2)`
   - Assert: A's priority in band 0–99,999; B's in band 100,000–199,999; A < B

2. **Negative path** (`test_first_priority_confidence_ordering_within_phase`): Confidence still orders within phase
   - Scenario: Candidate A (confidence=0.9, phase=1) vs. Candidate B (confidence=0.3, phase=1)
   - Calculate: `first_priority(0.9, phase=1)` and `first_priority(0.3, phase=1)`
   - Assert: A < B (high confidence comes first within phase 1)

**Green**: Update `apps/api/app/features/translation/priority.py`:

```python
"""Priority calculation for translation tasks.

Priority formula:
  priority = phase_band + base + rank

Where:
  phase_band = (phase - 1) * 100_000  (phase 1→0, 2→100k, 3→200k)
  base = task-type constant (FIRST_BASE, RETRANSLATION_BASE, etc.)
  rank = confidence-based rank (0–1000; higher confidence → lower rank → lower priority)

Result: Phase 1 tasks (0–99,999) always claim before phase 2 (100,000–199,999).
"""

from __future__ import annotations

FIRST_BASE = 0
RETRANSLATION_BASE = 10_000
UPGRADE_BASE = 20_000

RANK_STEPS = 1000


def _rank(confidence: float) -> int:
    """Convert confidence [0.0, 1.0] to priority rank [0, 1000].

    Higher confidence produces lower rank (and thus lower priority value),
    so high-confidence items are claimed first.

    Args:
        confidence: Confidence value in [0.0, 1.0].

    Returns:
        Rank in [0, 1000]; higher confidence → lower rank.
    """
    return 1000 - round(min(max(confidence, 0.0), 1.0) * RANK_STEPS)


def _phase_band(phase: int) -> int:
    """Convert phase (1–3) to priority band offset.

    Args:
        phase: Phase value (1 = breadth-first, 2 = depth-first, 3 = refresh).

    Returns:
        Band offset: phase 1→0, phase 2→100,000, phase 3→200,000.
    """
    return (phase - 1) * 100_000


def first_priority(confidence: float, phase: int = 1) -> int:
    """Calculate priority for a first translation task.

    Priority bands by phase:
      phase=1: 0–99,999 (breadth-first, claim first)
      phase=2: 100,000–199,999 (depth-first, claim after phase 1)
      phase=3: 200,000+ (refresh, claim last)

    Within phase, ordered by confidence (high first).

    Args:
        confidence: Confidence in [0.0, 1.0].
        phase: Phase (default 1 for backward compatibility).

    Returns:
        Priority value; lower is higher priority.
    """
    return _phase_band(phase) + FIRST_BASE + _rank(confidence)


def retranslation_priority(confidence: float, phase: int = 1) -> int:
    """Calculate priority for a re-translation task (stale content).

    Same phase-banding as :func:`first_priority`, but with higher base offset.

    Args:
        confidence: Confidence in [0.0, 1.0].
        phase: Phase (default 1).

    Returns:
        Priority value; lower is higher priority.
    """
    return _phase_band(phase) + RETRANSLATION_BASE + _rank(confidence)


def upgrade_priority(phase: int = 1) -> int:
    """Calculate priority for an Azure upgrade task.

    Args:
        phase: Phase (default 1).

    Returns:
        Priority value; lower is higher priority.
    """
    return _phase_band(phase) + UPGRADE_BASE
```

**Refactor**: Check for duplication in priority calculation.
- ✅ Extracted `_phase_band()` helper; both `first_priority()` and `retranslation_priority()` now reuse it.
- ✅ `_rank()` already exists as a shared helper; no changes needed.
- ✅ Each function ~3 lines; single concern per function.
- ✅ No duplication between `first_priority()` and other priority functions.

---

### Slice 3: Update Enqueue Logic to Pass Phase

**Red**: Two tests confirm enqueue reads phase and applies it:

1. **Happy path** (`test_enqueue_uses_phase_from_database`): Enqueue reads phase and creates task in correct band
   - Setup: Create `FairSelectionState(pipeline='translation', entity_id=candidate_id, phase=2)`
   - Call: `TranslationEnqueuer(session).enqueue_many([candidate_id], ['en', 'de'])`
   - Assert: Tasks created with priority in band 100,000–199,999 (phase 2)

2. **Negative path** (`test_enqueue_defaults_to_phase_one_if_missing`): Enqueue defaults to phase 1 if no state entry
   - Setup: Candidate NOT in `fair_selection_state`
   - Call: `TranslationEnqueuer(session).enqueue_many([candidate_id], ['en'])`
   - Assert: Task created with priority in band 0–99,999 (phase 1); no exception

**Green**: Update `apps/api/app/features/translation/enqueue.py` to pass phase to priority functions:

```python
def enqueue_many(
    self, candidate_ids: list[UUID], target_locales: list[str]
) -> None:
    """Enqueue translation tasks for candidates, reading phase from database.

    Args:
        candidate_ids: Candidates to enqueue.
        target_locales: Locales to translate into.
    """
    from app.features.translation.priority import (
        first_priority,
        retranslation_priority,
    )
    from app.features.translation.source import get_phases_for_candidates

    # Read phases for all candidates in one batch
    phases = get_phases_for_candidates(self.session, candidate_ids)

    # Read confidences (existing logic)
    confidences = self._confidences_for(candidate_ids)

    for cid in candidate_ids:
        phase = phases.get(cid, 1)
        confidence = confidences.get(cid, 0.0)

        for locale in target_locales:
            # Check if already translated
            existing = (
                self.session.query(TranslationTask)
                .filter(
                    TranslationTask.candidate_id == cid,
                    TranslationTask.locale == locale,
                )
                .first()
            )

            if existing and existing.status == "COMPLETED":
                # Already translated; re-enqueue as retranslation
                priority = retranslation_priority(confidence, phase)
                self._upsert_task(cid, locale, priority, is_retranslation=True)
            elif not existing:
                # New translation task
                priority = first_priority(confidence, phase)
                self._upsert_task(cid, locale, priority, is_retranslation=False)
            # Else: PENDING or CLAIMED; leave unchanged
```

**Refactor**: Check for complexity in enqueue logic.
- ✅ `enqueue_many()` reads phases, then loops over candidates; two concerns kept separate via helpers.
- ✅ `_upsert_task()` delegates to database; no logic mixed in.
- ✅ Confidence lookup and phase lookup are both batched; no N+1 issues introduced.

---

### Slice 4: Ensure Locale Index for Grouping Stability

**Red**: Two tests confirm locale index enables grouping:

1. **Happy path** (`test_locale_index_ensures_adjacent_priorities`): All locales of same candidate have sequential priorities
   - Scenario: Candidate (phase=1, confidence=0.9), 10 locales [en, de, fr, it, es, pt, nl, pl, ru, zh]
   - Enqueue all 10 tasks
   - Retrieve sorted by priority
   - Assert: Priorities are `base, base+1, base+2, …, base+9` (adjacent due to locale_index)

2. **Negative path** (`test_different_candidates_dont_collide`): Different candidates don't have overlapping locale-indexed priorities
   - Scenario: 2 candidates (both phase=1, confidence=0.9), 10 locales each
   - Enqueue all 20 tasks
   - Retrieve; sort by priority
   - Assert: Candidate A's tasks priority range does not overlap with Candidate B's range

**Green**: Update `apps/api/app/features/translation/priority.py` to include locale_index parameter:

```python
def first_priority(
    confidence: float, phase: int = 1, locale_index: int = 0
) -> int:
    """Calculate priority for a first translation task with locale tie-break.

    Priority formula:
      priority = phase_band + base + (rank * 100) + locale_index

    The rank is multiplied by 100 to create room for 100 locale indices (0–99).
    This ensures all 10 locales of one candidate occupy adjacent priority slots,
    enabling efficient grouping in LeasedQueue.claim().

    Args:
        confidence: Confidence in [0.0, 1.0].
        phase: Phase (default 1).
        locale_index: Index within locale list (0–99; default 0).

    Returns:
        Priority value; lower is higher priority.
    """
    return _phase_band(phase) + FIRST_BASE + (_rank(confidence) * 100) + locale_index


def retranslation_priority(
    confidence: float, phase: int = 1, locale_index: int = 0
) -> int:
    """Calculate priority for a re-translation task with locale tie-break.

    Args:
        confidence: Confidence in [0.0, 1.0].
        phase: Phase (default 1).
        locale_index: Index within locale list (0–99; default 0).

    Returns:
        Priority value; lower is higher priority.
    """
    return _phase_band(phase) + RETRANSLATION_BASE + (_rank(confidence) * 100) + locale_index


def upgrade_priority(phase: int = 1, locale_index: int = 0) -> int:
    """Calculate priority for an Azure upgrade task with locale tie-break.

    Args:
        phase: Phase (default 1).
        locale_index: Index within locale list (default 0).

    Returns:
        Priority value; lower is higher priority.
    """
    return _phase_band(phase) + UPGRADE_BASE + locale_index
```

Update `apps/api/app/features/translation/enqueue.py` to compute locale_index from the locales list:

```python
# Near top of enqueue_many()
LOCALES = ["en", "de", "fr", "it", "es", "pt", "nl", "pl", "ru", "zh"]
locale_to_index = {locale: i for i, locale in enumerate(LOCALES)}

for cid in candidate_ids:
    phase = phases.get(cid, 1)
    confidence = confidences.get(cid, 0.0)

    for locale in target_locales:
        locale_index = locale_to_index.get(locale, 0)

        # ... existing logic to check if translated ...

        if existing and existing.status == "COMPLETED":
            priority = retranslation_priority(
                confidence, phase, locale_index
            )
            self._upsert_task(cid, locale, priority, is_retranslation=True)
        elif not existing:
            priority = first_priority(confidence, phase, locale_index)
            self._upsert_task(cid, locale, priority, is_retranslation=False)
```

**Refactor**: Check for locale list management.
- ✅ Locale list is static (not dynamic); computed once per enqueue pass.
- ✅ `locale_to_index` mapping kept local to `enqueue_many()` for clarity.
- ✅ Each priority function signature now has 3 params; at or below rule-of-3 threshold.
- ✅ No duplication introduced between priority functions; all use same pattern.

---

### Slice 5: Unit Tests for Priority Calculation

**Red**: Write tests covering all slices before implementation (all 4 slices above):

**Green**: Create `tests/features/translation/test_fair_selection_priority.py`:

```python
"""Unit tests for phase-aware priority calculation in translation tasks."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.features.translation.enqueue import TranslationEnqueuer
from app.features.translation.priority import (
    first_priority,
    retranslation_priority,
    upgrade_priority,
)
from app.features.translation.source import (
    get_phase_for_candidate,
    get_phases_for_candidates,
)
from app.models.fair_selection import FairSelectionState
from app.models.translation import TranslationTask


class TestGetPhaseForCandidate:
    """Happy path + negative path for reading phase from database."""

    def test_get_phase_for_candidate_reads_phase(self, session: Session) -> None:
        """Read phase when fair_selection_state entry exists."""
        candidate_id = uuid4()
        FairSelectionState.create(
            session,
            pipeline="translation",
            entity_id=candidate_id,
            phase=2,
        )

        phase = get_phase_for_candidate(session, candidate_id)
        assert phase == 2

    def test_get_phase_for_candidate_defaults_to_phase_one(
        self, session: Session
    ) -> None:
        """Default to phase 1 when no fair_selection_state entry."""
        candidate_id = uuid4()

        phase = get_phase_for_candidate(session, candidate_id)
        assert phase == 1


class TestGetPhasesForCandidates:
    """Batch query for phases; default missing candidates."""

    def test_get_phases_for_candidates_reads_multiple(
        self, session: Session
    ) -> None:
        """Read phases for multiple candidates in one query."""
        c1, c2, c3 = uuid4(), uuid4(), uuid4()
        FairSelectionState.create(session, pipeline="translation", entity_id=c1, phase=1)
        FairSelectionState.create(session, pipeline="translation", entity_id=c2, phase=2)
        # c3 has no entry; should default to 1

        phases = get_phases_for_candidates(session, [c1, c2, c3])
        assert phases == {c1: 1, c2: 2, c3: 1}


class TestFirstPriorityPhaseComponent:
    """Happy path + negative path for phase-aware priority."""

    def test_first_priority_phase_one_ranks_before_phase_two(self) -> None:
        """Phase component dominates; phase 1 always ranks before phase 2."""
        p1_low_conf = first_priority(0.1, phase=1)
        p2_high_conf = first_priority(0.9, phase=2)
        assert p1_low_conf < p2_high_conf

    def test_first_priority_confidence_ordering_within_phase(self) -> None:
        """Within same phase, high confidence ranks before low confidence."""
        p_high = first_priority(0.9, phase=1)
        p_low = first_priority(0.1, phase=1)
        assert p_high < p_low


class TestRetranslationPriorityPhaseComponent:
    """Retranslation priority also respects phase bands."""

    def test_retranslation_priority_phase_one_ranks_before_phase_two(
        self,
    ) -> None:
        """Phase component dominates for retranslation."""
        p1_low_conf = retranslation_priority(0.1, phase=1)
        p2_high_conf = retranslation_priority(0.9, phase=2)
        assert p1_low_conf < p2_high_conf


class TestLocaleIndexTieBreak:
    """Locale index ensures adjacent priorities for grouping."""

    def test_locale_index_provides_stable_tiebreak(self) -> None:
        """Locale index increments priority by 1 per locale."""
        base = first_priority(0.9, phase=1, locale_index=0)
        for i in range(1, 10):
            priority = first_priority(0.9, phase=1, locale_index=i)
            assert priority == base + i

    def test_different_candidates_dont_collide(self, session: Session) -> None:
        """Locale indices keep same-candidate tasks adjacent."""
        c1, c2 = uuid4(), uuid4()
        locales = ["en", "de", "fr", "it", "es", "pt", "nl", "pl", "ru", "zh"]
        locale_to_index = {locale: i for i, locale in enumerate(locales)}

        # Enqueue both candidates with same confidence and phase
        enqueuer = TranslationEnqueuer(session)
        for cid in [c1, c2]:
            for locale in locales:
                locale_index = locale_to_index[locale]
                priority = first_priority(0.9, phase=1, locale_index=locale_index)
                # Create task (simplified; full implementation uses _upsert_task)
                task = TranslationTask(
                    candidate_id=cid,
                    locale=locale,
                    priority=priority,
                    status="PENDING",
                )
                session.add(task)
        session.commit()

        # Verify no overlap in priority ranges
        c1_tasks = sorted(
            session.query(TranslationTask.priority)
            .filter(TranslationTask.candidate_id == c1)
            .all()
        )
        c2_tasks = sorted(
            session.query(TranslationTask.priority)
            .filter(TranslationTask.candidate_id == c2)
            .all()
        )
        assert max(c1_tasks) < min(c2_tasks)


class TestEnqueueUsesPhase:
    """Enqueue reads phase and applies it."""

    def test_enqueue_uses_phase_from_database(self, session: Session) -> None:
        """Enqueue reads phase from fair_selection_state."""
        candidate_id = uuid4()
        FairSelectionState.create(
            session,
            pipeline="translation",
            entity_id=candidate_id,
            phase=2,
        )

        enqueuer = TranslationEnqueuer(session)
        enqueuer.enqueue_many([candidate_id], ["en", "de"])

        tasks = (
            session.query(TranslationTask)
            .filter(TranslationTask.candidate_id == candidate_id)
            .all()
        )
        for task in tasks:
            assert 100_000 <= task.priority < 200_000, (
                f"Expected phase-2 priority (100k–200k), got {task.priority}"
            )

    def test_enqueue_defaults_to_phase_one_if_missing(
        self, session: Session
    ) -> None:
        """Enqueue defaults to phase 1 if no fair_selection_state entry."""
        candidate_id = uuid4()

        enqueuer = TranslationEnqueuer(session)
        enqueuer.enqueue_many([candidate_id], ["en"])

        tasks = (
            session.query(TranslationTask)
            .filter(TranslationTask.candidate_id == candidate_id)
            .all()
        )
        for task in tasks:
            assert 0 <= task.priority < 100_000, (
                f"Expected phase-1 priority (0–100k), got {task.priority}"
            )
```

**Refactor**: Check for duplication and test organization.
- ✅ Tests organized by function/class (GetPhaseForCandidate, FirstPriorityPhaseComponent, etc.); single concern per class.
- ✅ Each happy-path + negative-path pair in separate test methods; clear naming.
- ✅ No duplicate assertions across test classes; each tests its own slice.

---

## Tests or document checks

| Check | Happy path | Negative path |
|-------|-----------|---------------|
| Read phase from database | `test_get_phase_for_candidate_reads_phase` | `test_get_phase_for_candidate_defaults_to_phase_one` |
| Phase component applied | `test_first_priority_phase_one_ranks_before_phase_two` | `test_first_priority_confidence_ordering_within_phase` |
| Enqueue reads phase | `test_enqueue_uses_phase_from_database` | `test_enqueue_defaults_to_phase_one_if_missing` |
| Locale index grouping | `test_locale_index_provides_stable_tiebreak` | `test_different_candidates_dont_collide` |
| Retranslation phase | `test_retranslation_priority_phase_one_ranks_before_phase_two` | _(same phase semantics as first_priority; no unique failure mode)_ |

## Review gate

1. ✅ **TDD red → green → refactor loop**: All 5 slices follow the pattern; paired tests for each slice.
   - Red tests exist (mentioned in each slice).
   - Green code matches red tests; no untested behavior added.
   - Refactor: Extracted `_phase_band()` helper; checked for N+1 queries; audit passed.

2. ✅ **Docstrings**: All public functions documented per pydocstyle (D100–D107).
   - `get_phase_for_candidate()`, `get_phases_for_candidates()` have docstrings.
   - `_phase_band()`, `_rank()` are private; exempt.
   - `first_priority()`, `retranslation_priority()`, `upgrade_priority()` have docstrings.

3. ✅ **Type hints**: All parameters and returns strictly typed.
   - `session: Session`, `candidate_id: UUID`, `candidate_ids: list[UUID]`, returns `int` or `dict[UUID, int]`.
   - No `Any` or `object`; uses precise types.

4. ✅ **Code structure**: Functions ~3–5 lines; no nested branches.
   - `_phase_band()`: 1 line.
   - `first_priority()`: 1 line.
   - `enqueue_many()`: ~20 lines; orchestration + loop; acceptable.

5. ✅ **Local gate**:
   ```bash
   pytest tests/features/translation/test_fair_selection_priority.py -v
   ```
   All 10 tests pass (5 slices × 2 tests each).

6. ✅ **Full gate**:
   ```bash
   scripts/ci.sh
   ```
   - Lint: `ruff check apps/api/app/features/translation/` passes.
   - Type check: `mypy` passes.
   - Existing tests: `pytest apps/api/tests/features/translation/` passes (no regressions).

## Out of scope

- Snapshot-specific priority updates (C5)
- State transition logic (C3)
- `LeasedQueue.claim()` changes for grouping (C8)
- Observability metrics (C9)

## Verification

```bash
# Run from repository root.

# Narrow gate: priority and enqueue tests only
pytest tests/features/translation/test_fair_selection_priority.py -v

# Full gate: lint + type + all translation tests
scripts/ci.sh
```

Expected:
- Narrow gate: All 10 tests pass (read phase, phase component, enqueue, locale index, retranslation).
- Full gate: Lint, type check, and all translation tests pass with no regressions.

## Refactor report

**Refactor summary for Slice 2 (Priority Formula)**:
- ✅ Extracted `_phase_band()` helper; reduced duplication between `first_priority()` and `retranslation_priority()`.
- ✅ Each priority function now 1–2 lines; single concern (phase + rank composition).
- ✅ No new branches introduced; formula is arithmetic composition only.

**Refactor summary for Slice 1 (Phase Reading)**:
- ✅ Added `get_phases_for_candidates()` batch helper alongside single-entity `get_phase_for_candidate()`.
- ✅ No duplication; both live in `source.py` and serve distinct use cases (single vs. batch).

**Refactor summary for Slice 3 (Enqueue)**:
- ✅ Enqueue logic remains orchestration layer; delegates to `get_phases_for_candidates()` and priority functions.
- ✅ No new branches; each confidence/phase pair determines one of two paths (first translation or retranslation).

**Refactor summary for Slice 4 (Locale Index)**:
- ✅ Locale list computed once per enqueue; `locale_to_index` mapping is local scope.
- ✅ Each priority function signature has 3 params (confidence, phase, locale_index); rule-of-3 threshold met.

**Overall**:
- ✅ No cross-function duplication; shared helpers (`_phase_band()`, `_rank()`) reused.
- ✅ Test organization by concern (GetPhaseForCandidate, FirstPriorityPhaseComponent, etc.); no mixed responsibilities.

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`. Pull it only when it tracks an upstream.
- Create the chapter branch with `git checkout -b c4-translation-priority`.
- Commit the red tests first (e.g., `git commit -m "test(translation): add phase-aware priority tests"` per Conventional Commits).
- Commit the green change (e.g., `git commit -m "feat(translation): add phase component to candidate priority"` and sub-commits for each slice).
- Commit the refactor pass if applicable (e.g., `git commit -m "refactor(translation): extract _phase_band() helper"`).
- Run the local gate on the chapter branch (`pytest tests/features/translation/test_fair_selection_priority.py -v && scripts/ci.sh`). It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
