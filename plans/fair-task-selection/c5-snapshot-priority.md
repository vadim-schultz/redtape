---
id: C5
depends_on:
  - C1
  - C2
touches:
  - apps/api/app/features/translation/snapshot_enqueue.py
  - apps/api/app/features/translation/priority.py
  - apps/api/tests/test_translation_enqueue.py
execution: chapter-implementer
---

# C5: Update Translation Priority (Snapshots)

**Depends on:** C1, C2 · **Architecture:** 00-architecture.md § Translation (Snapshots) · **Rollout:** 01-rollout.md

## Goal

Modify snapshot translation task priority calculation to include phase component, ensuring phase-1 tasks always rank above phase-2. Snapshots are grouped by `catalogue_service_id` (page), so all locales of one page claim together before moving to the next.

## Read first

- **00-architecture.md**: Translation (Snapshots) section. Priority formula bands (phase 1 = 0–99,999, phase 2 = 100,000–199,999). Grouping by `catalogue_service_id`.
- **01-rollout.md**: Snapshot-specific backfill rules for `fair_selection_state`.

## Coordination scope

**Add:**

- None. Use existing test file `apps/api/tests/test_translation_enqueue.py` (snapshot tests are already colocated).

**Edit:**

- `apps/api/app/features/translation/priority.py` — snapshot priority functions to accept phase parameter.
- `apps/api/app/features/translation/snapshot_enqueue.py` — enqueue logic to read phase and apply it to snapshot tasks.
- `apps/api/tests/test_translation_enqueue.py` — add snapshot-specific phase tests.

**Do not edit:**

- `apps/api/app/features/translation/source.py` — phase lookup helpers added by C4.
- `apps/api/app/features/translation/enqueue.py` — candidate-specific logic (C4).
- `apps/api/app/models/fair_selection.py` — schema defined by C2.

## Work items

### Slice 1: Read Phase for Pages

**Red**: Two tests:

1. **Happy path** (`test_get_phase_for_page_reads_from_state`):
   - Setup: `FairSelectionState(pipeline='translation', entity_id=page_id, phase=2, ...)`
   - Call: `get_phase_for_page(session, page_id)` → returns `2`
   - Assert: Correct phase read from database

2. **Negative path** (`test_get_phase_for_page_defaults_to_one_when_not_found`):
   - Setup: No entry in `fair_selection_state` for `page_id`
   - Call: `get_phase_for_page(session, page_id)` → returns `1`
   - Assert: Defaults to phase 1; doesn't crash or return `None`

**Green**: Add helper functions to `apps/api/app/features/translation/source.py`:

```python
def get_phase_for_page(session: Session, catalogue_service_id: UUID) -> int:
    """Read phase for a page; default to phase 1 if not found."""
    state = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == 'translation',
        FairSelectionState.entity_id == catalogue_service_id
    ).first()
    return state.phase if state else 1


def get_phases_for_pages(session: Session, page_ids: Iterable[UUID]) -> dict[UUID, int]:
    """Read phases for multiple pages in one batch query."""
    page_ids_list = list(page_ids)
    if not page_ids_list:
        return {}

    states = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == 'translation',
        FairSelectionState.entity_id.in_(page_ids_list)
    ).all()

    result = {s.entity_id: s.phase for s in states}
    # Fill in defaults for missing entries
    for page_id in page_ids_list:
        if page_id not in result:
            result[page_id] = 1

    return result
```

**Refactor**: Check that `get_phases_for_pages()` is used in batch operations (not called per-page inside a loop). No new extraction needed; mirrors C4's pattern exactly.

✅ No refactor needed — copied pattern from C4; avoids N+1 queries.

---

### Slice 2: Compute Page Confidence (Max of Mentioning Candidates)

**Red**: Two tests:

1. **Happy path** (`test_page_confidence_returns_max_of_candidate_scores`):
   - Setup: Page with 3 candidate mentions (scores 0.5, 0.9, 0.3)
   - Call: `page_confidence([0.5, 0.9, 0.3])` → returns `0.9`
   - Assert: Returns maximum confidence

2. **Negative path** (`test_page_confidence_returns_zero_when_no_candidates`):
   - Setup: Page with no mentions (empty confidence list)
   - Call: `page_confidence([])` → returns `0.0`
   - Assert: Handles empty list gracefully (already tested in C4; verify snapshot version works)

**Green**: The function `page_confidence()` already exists in `priority.py` and correctly returns `max(confidences, default=0.0)`. Verify snapshot_enqueue passes full candidate confidence tuple from `PageState.confidences`:

```python
# In snapshot_enqueue.py, PageState already stores:
@dataclass(frozen=True, slots=True)
class PageState:
    catalogue_service_id: UUID
    artifact_sha256: str
    stored: Mapping[str, str]
    open_locales: frozenset[str]
    confidences: tuple[float, ...]  # <-- Existing field: confidence of each mention

    @property
    def has_candidates(self) -> bool:
        """Return whether a candidate mentions the page."""
        return bool(self.confidences)
```

Existing code in `_priority()` already uses `page_confidence(page.confidences)`, so no change is needed here.

**Refactor**: The existing `page_confidence()` function is already correct. No refactor needed.

✅ No refactor needed — existing implementation correct; snapshot_enqueue already uses it.

---

### Slice 3: Modify Snapshot Priority Functions to Include Phase Component

**Red**: Two tests:

1. **Happy path** (`test_snapshot_first_priority_includes_phase_band`):
   - Scenario: Page with max candidate confidence 0.9, phase=1 vs. phase=2
   - Calculate: `snapshot_first_priority([0.9], phase=1)` vs. `snapshot_first_priority([0.9], phase=2)`
   - Assert: Phase 1 priority is in band 0–99,999; phase 2 is in band 100,000–199,999
   - Assert: Phase 1 < phase 2 (phase 1 always claims first)

2. **Negative path** (`test_snapshot_first_priority_preserves_confidence_order_within_phase`):
   - Scenario: Two pages (confidence 0.9 vs. 0.3), both phase=1
   - Calculate: `snapshot_first_priority([0.9], phase=1)` vs. `snapshot_first_priority([0.3], phase=1)`
   - Assert: High confidence < low confidence within same phase (confidence still matters)

**Green**: Update `apps/api/app/features/translation/priority.py`:

Add phase parameter to snapshot functions:

```python
def snapshot_first_priority(confidences: Iterable[float], phase: int = 1) -> int:
    """Return the priority of a page's first translation, ranked by its best candidate and phase.

    Phase component:
      phase=1: 0–99,999 (breadth-first)
      phase=2: 100,000–199,999 (depth-first)
      phase=3: 200,000+ (refresh)

    Within phase, ordered by confidence (high first).
    """
    phase_band = _phase_band(phase)
    confidence = page_confidence(confidences)
    rank = _rank(confidence)
    return phase_band + FIRST_BASE + rank


def snapshot_retranslation_priority(confidences: Iterable[float], phase: int = 1) -> int:
    """Return the priority of re-translating a page, ranked by its best candidate and phase."""
    phase_band = _phase_band(phase)
    confidence = page_confidence(confidences)
    rank = _rank(confidence)
    return phase_band + RETRANSLATION_BASE + rank
```

**Refactor**: Check for duplication between `snapshot_first_priority()` and `first_priority()`. Both call `_phase_band(phase)` and `_rank(confidence)`:

Existing structure (after C4):
```python
def _phase_band(phase: int) -> int:
    """Convert phase (1–3) to priority band offset."""
    return (phase - 1) * 100_000

def first_priority(confidence: float, phase: int = 1) -> int:
    return _phase_band(phase) + FIRST_BASE + _rank(confidence)

def snapshot_first_priority(confidences: Iterable[float], phase: int = 1) -> int:
    # Differs only in: uses page_confidence(confidences) instead of confidence directly
    return _phase_band(phase) + FIRST_BASE + _rank(page_confidence(confidences))
```

Both functions follow the same pattern. The only difference is input transformation (single confidence vs. iterable). No extraction needed; both are simple and clear at their current size (~2–3 lines each).

✅ No refactor needed — pattern is already DRY via `_phase_band()` and `_rank()` helpers. Snapshot variants correctly delegate to `page_confidence()`.

---

### Slice 4: Update Snapshot Enqueue to Read Phase and Apply It

**Red**: Two tests:

1. **Happy path** (`test_snapshot_enqueue_applies_phase_to_priority`):
   - Setup: Page with phase=2 in `fair_selection_state`; candidate confidence 0.9
   - Call: `enqueuer.load([page_id])` → `PageState` with phase and confidence
   - Call: `enqueuer.queue([page_state], enqueuer.every_locale)`
   - Assert: Task created with priority in band 100,000–199,999 (phase 2)
   - Assert: Task is queryable from database with correct phase-2 priority

2. **Negative path** (`test_snapshot_enqueue_defaults_to_phase_one_when_not_in_state`):
   - Setup: Page NOT in `fair_selection_state`
   - Call: `enqueuer.load([page_id])` → `PageState` with no phase entry
   - Call: `enqueuer.queue([page_state], enqueuer.every_locale)`
   - Assert: Task created with priority in band 0–99,999 (phase 1, default)

**Green**: Update `apps/api/app/features/translation/snapshot_enqueue.py`:

Modify `SnapshotEnqueuer` to read phases and pass to priority functions:

```python
from app.features.translation.source import get_phases_for_pages

class SnapshotEnqueuer:
    """Queue the snapshot translation of procedure pages into the target locales, one open task per page and locale."""

    def __init__(self, session: Session, locales: Sequence[str] | None = None) -> None:
        """Bind the enqueuer to ``session`` and the target ``locales`` (the configured ones by default)."""
        self._session = session
        self._locales = tuple(settings.translation_target_locale_codes if locales is None else locales)
        self._pages = ProcedurePageReads.for_session(session)
        self._index = SnapshotRepository(session)
        self._tasks = TaskRepository(session)
        self._source = SourceRepository(session)

    def load(self, shas: Mapping[UUID, str]) -> list[PageState]:
        """Read each page in ``shas``, which maps a catalogue row to the artifact sha it is translated from."""
        if not shas or not self._locales:
            return []
        pages = list(shas)
        candidates = self._pages.candidate_ids_by_page(pages)
        scores = self._source.confidences_for(sorted({c for ids in candidates.values() for c in ids}))
        stored, open_locales = self._index.stored_shas(pages), self._index.open_locales(pages)

        # NEW: Read phases for all pages in one batch
        phases = get_phases_for_pages(self._session, pages)

        return [
            PageState(
                page,
                sha,
                stored.get(page, {}),
                open_locales.get(page, frozenset()),
                _scores_of(candidates.get(page, ()), scores),
                phases.get(page, 1),  # NEW: Include phase; defaults to 1
            )
            for page, sha in shas.items()
        ]

    # ... rest of class ...
```

Extend `PageState` to include phase:

```python
@dataclass(frozen=True, slots=True)
class PageState:
    """One procedure page as the enqueue reads it.

    ``stored`` maps a locale to the artifact sha its stored translation was made from; a skip marker counts as stored.
    ``open_locales`` are the locales with an open (pending or claimed) task. ``confidences`` holds the card confidence of
    each candidate that mentions the page. ``phase`` is the phase from fair_selection_state, defaulting to 1.
    """

    catalogue_service_id: UUID
    artifact_sha256: str
    stored: Mapping[str, str]
    open_locales: frozenset[str]
    confidences: tuple[float, ...]
    phase: int = 1  # NEW: Phase for this page
```

Modify `_priority()` to pass phase:

```python
def _priority(page: PageState, locale: str) -> int:
    """Rank a first translation by the page's best candidate and phase, and a stale one behind every first translation."""
    if locale in page.stored:
        return snapshot_retranslation_priority(page.confidences, phase=page.phase)  # NEW: pass phase
    return snapshot_first_priority(page.confidences, phase=page.phase)  # NEW: pass phase
```

**Refactor**: Check for complexity in `_priority()` and `_upsert()`:

Current code is simple:
```python
def _priority(page: PageState, locale: str) -> int:
    """..."""
    if locale in page.stored:
        return snapshot_retranslation_priority(page.confidences, phase=page.phase)
    return snapshot_first_priority(page.confidences, phase=page.phase)

def _upsert(self, page: PageState, locale: str) -> bool:
    return self._tasks.upsert_snapshot_pending(
        (page.catalogue_service_id, locale), page.artifact_sha256, _priority(page, locale)
    )
```

Both are already concise (2–4 lines). No extraction needed.

✅ No refactor needed — `_priority()` and `_upsert()` remain simple, single-concern helpers.

---

### Slice 5: Integration Test (Page Grouping + Phase Ordering)

**Red**: Two tests:

1. **Happy path** (`test_snapshot_phase_one_pages_rank_before_phase_two`):
   - Setup: 2 pages (A and B), A with phase=1 confidence=0.3, B with phase=2 confidence=0.9
   - Enqueue both pages for 2 locales (en, de)
   - Assert: Task count = 4 (2 pages × 2 locales)
   - Assert: Task priorities sorted: All of page A's tasks (phase 1) come before all of page B's tasks (phase 2)
   - Assert: Page A's priorities in band 0–99,999; page B's in band 100,000–199,999

2. **Negative path** (`test_snapshot_pages_of_same_phase_ordered_by_confidence`):
   - Setup: 2 pages (A and B), both phase=1, A confidence=0.9, B confidence=0.3
   - Enqueue both pages for 2 locales (en, de)
   - Assert: Task count = 4
   - Assert: When sorted by priority, page A's tasks (high confidence) come before page B's (low confidence) within phase 1
   - Assert: Within each page, all locales are adjacent (grouped by page)

**Green**: Add tests to `apps/api/tests/test_translation_enqueue.py`:

```python
def test_snapshot_phase_one_pages_rank_before_phase_two(
    db_session: Session,
) -> None:
    """Verify phase-1 snapshot tasks rank before phase-2 tasks."""
    # Setup: Two pages, one phase 1 (low confidence), one phase 2 (high confidence)
    page_a = make_page(db_session, confidence=0.3)  # Phase 1 (default)
    page_b = make_page(db_session, confidence=0.9)

    # Set page B to phase 2
    FairSelectionState.create(
        db_session,
        pipeline='translation',
        entity_id=page_b.catalogue_service_id,
        phase=2,
    )
    db_session.commit()

    # Enqueue both for 2 locales
    enqueuer_inst = enqueuer(db_session, ("en", "de"))
    totals = enqueuer_inst.enqueue_pages([page_a.catalogue_service_id, page_b.catalogue_service_id])

    # Retrieve tasks; sort by priority
    tasks = (
        db_session.query(SnapshotTranslationTask)
        .order_by(SnapshotTranslationTask.priority.asc())
        .all()
    )

    # Assert: 4 tasks (2 pages × 2 locales)
    assert len(tasks) == 4, f"Expected 4 tasks, got {len(tasks)}"
    assert totals.enqueued == 4

    # Assert: Page A's tasks (phase 1) come first
    page_a_tasks = [t for t in tasks if t.catalogue_service_id == page_a.catalogue_service_id]
    page_b_tasks = [t for t in tasks if t.catalogue_service_id == page_b.catalogue_service_id]

    assert len(page_a_tasks) == 2, f"Expected 2 tasks for page A, got {len(page_a_tasks)}"
    assert len(page_b_tasks) == 2, f"Expected 2 tasks for page B, got {len(page_b_tasks)}"

    # Assert: All page A tasks rank before all page B tasks
    max_a_priority = max(t.priority for t in page_a_tasks)
    min_b_priority = min(t.priority for t in page_b_tasks)
    assert max_a_priority < min_b_priority, (
        f"All page A (phase 1) priorities should be < page B (phase 2). "
        f"Max A: {max_a_priority}, Min B: {min_b_priority}"
    )

    # Assert: Page A priorities in band 0–99,999; page B in 100,000–199,999
    for task in page_a_tasks:
        assert 0 <= task.priority < 100_000, f"Page A priority {task.priority} not in phase-1 band"
    for task in page_b_tasks:
        assert 100_000 <= task.priority < 200_000, f"Page B priority {task.priority} not in phase-2 band"


def test_snapshot_pages_of_same_phase_ordered_by_confidence_and_grouped_by_page(
    db_session: Session,
) -> None:
    """Verify within same phase, pages rank by confidence; locales of same page are grouped."""
    # Setup: Two pages, both phase 1, different confidences
    page_high = make_page(db_session, confidence=0.9)  # High confidence
    page_low = make_page(db_session, confidence=0.3)   # Low confidence

    # Both default to phase 1
    db_session.commit()

    # Enqueue both for 2 locales
    enqueuer_inst = enqueuer(db_session, ("en", "de"))
    totals = enqueuer_inst.enqueue_pages([page_high.catalogue_service_id, page_low.catalogue_service_id])

    # Retrieve tasks; sort by priority
    tasks = (
        db_session.query(SnapshotTranslationTask)
        .order_by(SnapshotTranslationTask.priority.asc())
        .all()
    )

    # Assert: 4 tasks (2 pages × 2 locales)
    assert len(tasks) == 4
    assert totals.enqueued == 4

    # Assert: Page with high confidence comes first
    page_high_tasks = [t for t in tasks if t.catalogue_service_id == page_high.catalogue_service_id]
    page_low_tasks = [t for t in tasks if t.catalogue_service_id == page_low.catalogue_service_id]

    max_high_priority = max(t.priority for t in page_high_tasks)
    min_low_priority = min(t.priority for t in page_low_tasks)
    assert max_high_priority < min_low_priority, (
        f"High confidence page should rank before low confidence page within phase 1. "
        f"Max high: {max_high_priority}, Min low: {min_low_priority}"
    )

    # Assert: Locales of same page are adjacent in priority (grouped)
    # For page_high_tasks: priorities should be [base, base+1] for the two locales
    high_priorities_sorted = sorted(t.priority for t in page_high_tasks)
    if len(high_priorities_sorted) == 2:
        # Locales should be adjacent (differ by 1 due to locale_index in priority formula)
        assert (
            high_priorities_sorted[1] - high_priorities_sorted[0] <= 1
        ), f"Page high locales not grouped: {high_priorities_sorted}"
```

Helper function to create a page with candidate:

```python
def make_page(db_session: Session, confidence: float) -> CataloguePageCandidate:
    """Create a page with a mention of a candidate at given confidence."""
    # Create catalogue entry, page, candidate, mention
    candidate = make_candidate(db_session, score=confidence)
    # (Assuming snapshot fixture provides catalogue and page; adjust per existing test setup)
    page = db_session.query(CataloguePageCandidate).filter(...).first()  # Retrieve or create
    make_mention(db_session, candidate, page)
    return page
```

**Refactor**: Check for test duplication with C4 candidate tests. Both test phase ordering and confidence ordering, but at different levels (candidate vs. page). No extraction needed; tests target different models.

✅ No refactor needed — snapshot tests are independent of candidate tests; different models, different grouping keys.

---

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Read phase for page | `test_get_phase_for_page_reads_from_state` | `test_get_phase_for_page_defaults_to_one_when_not_found` |
| Page confidence (max of candidates) | `test_page_confidence_returns_max_of_candidate_scores` | `test_page_confidence_returns_zero_when_no_candidates` |
| Snapshot priority includes phase | `test_snapshot_first_priority_includes_phase_band` | `test_snapshot_first_priority_preserves_confidence_order_within_phase` |
| Snapshot enqueue applies phase | `test_snapshot_enqueue_applies_phase_to_priority` | `test_snapshot_enqueue_defaults_to_phase_one_when_not_in_state` |
| Phase ordering + grouping | `test_snapshot_phase_one_pages_rank_before_phase_two` | `test_snapshot_pages_of_same_phase_ordered_by_confidence_and_grouped_by_page` |

## Review gate

Before merging, ensure:

1. ✅ All 10 TDD test pairs (happy + negative for each of 5 slices) pass locally
2. ✅ Snapshot task priorities are correctly calculated (phase band applied, confidence preserved)
3. ✅ Pages of the same phase are grouped correctly (all locales of one page claimed before next page)
4. ✅ Phase defaults to 1 when no entry in `fair_selection_state`
5. ✅ No N+1 queries: `get_phases_for_pages()` batches lookups
6. ✅ No duplication introduced: snapshot functions mirror C4 pattern exactly
7. ✅ Ruff lint, type check (`mypy`), and existing test suite pass
8. ✅ Database remains backfill-compatible: phase is optional, defaults via code

## Out of scope

- **C1**: Phase state design and table schema (already done)
- **C2**: Schema migration and backfill (already done)
- **C4**: Candidate translation priority (separate chapter)
- **C3**: Phase transition logic (separate chapter)
- **C6–C8**: Other pipelines and queue claim logic (separate chapters)

## Verification

```bash
# Run from the repository root.

# Slice 1: Phase reader tests
pytest apps/api/tests/test_translation_enqueue.py::test_get_phase_for_page_reads_from_state -v
pytest apps/api/tests/test_translation_enqueue.py::test_get_phase_for_page_defaults_to_one_when_not_found -v

# Slice 2: Confidence computation (already exists; verify no regression)
pytest apps/api/tests/ -k "page_confidence" -v

# Slice 3: Priority formula
pytest apps/api/tests/test_translation_enqueue.py::test_snapshot_first_priority_includes_phase_band -v
pytest apps/api/tests/test_translation_enqueue.py::test_snapshot_first_priority_preserves_confidence_order_within_phase -v

# Slice 4: Enqueue applies phase
pytest apps/api/tests/test_translation_enqueue.py::test_snapshot_enqueue_applies_phase_to_priority -v
pytest apps/api/tests/test_translation_enqueue.py::test_snapshot_enqueue_defaults_to_phase_one_when_not_in_state -v

# Slice 5: Integration
pytest apps/api/tests/test_translation_enqueue.py::test_snapshot_phase_one_pages_rank_before_phase_two -v
pytest apps/api/tests/test_translation_enqueue.py::test_snapshot_pages_of_same_phase_ordered_by_confidence_and_grouped_by_page -v

# Full test suite for translation module
pytest apps/api/tests/test_translation_enqueue.py -v

# Lint and type check
ruff check apps/api/app/features/translation/
mypy apps/api/app/features/translation/

# Full CI
./scripts/ci.sh
```

Expected: All tests pass; lint and type check clean; no warnings about N+1 queries or unused code.

## Refactor report

**Slice 1 (Phase reader)**: No refactor needed — mirrors C4 pattern exactly. `get_phases_for_pages()` batches queries.

**Slice 2 (Confidence computation)**: No refactor needed — existing `page_confidence()` function already correct. Snapshot_enqueue already passes full tuple.

**Slice 3 (Priority formula)**: No refactor needed — pattern is already DRY via `_phase_band()` and `_rank()` helpers. Snapshot variants correctly delegate to `page_confidence()`. Both `snapshot_first_priority()` and `snapshot_retranslation_priority()` are concise (~3 lines) and follow identical structure to their candidate counterparts.

**Slice 4 (Enqueue + PageState)**: No refactor needed — `_priority()` and `_upsert()` remain single-concern, concise helpers (2–4 lines each). PageState extension is minimal (one field).

**Slice 5 (Integration tests)**: No refactor needed — snapshot tests are independent of candidate tests; they target different models and grouping keys. No extraction justified at one caller per test.

---

## Git workflow

- Check out the loop branch with `git checkout feat/plans-pipeline-optimisation`. Pull it only when it tracks an upstream.
- Create the chapter branch with `git checkout -b feat/c5-snapshot-priority`.
- Commit the red tests first (TDD red phase for all 5 slices), then green implementations per slice, then refactor audits per slice.
- Run the local gate on the chapter branch: `pytest apps/api/tests/test_translation_enqueue.py -v && ./scripts/ci.sh`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
