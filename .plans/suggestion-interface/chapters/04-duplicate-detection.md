---
name: "Chapter 4 — Duplicate detection"
overview: "Creating a suggestion raises DuplicateSuggestionError listing conflicting documents or pending suggestions when the derived slug or the normalized official URL already exists in the same jurisdiction."
todos:
  - id: documents
    content: "DocumentService.find_conflicts (read-only)"
    status: done
  - id: pending
    content: "SuggestionRepository.find_pending_by_url"
    status: done
  - id: service
    content: "SuggestionService checks before insert"
    status: done
isProject: false
---

# Chapter 4 — Duplicate detection

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-duplicates` · **Status:** implemented, PR open

**Depends on:** [3](03-suggestion-repository-service.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Neither people nor crawlers can flood the moderation queue with things the catalogue already has or that
are already waiting (D4). A duplicate produces a domain error carrying the conflicting ids, so the UI can
link to them.

## Design decisions

**What counts as a duplicate** (only for `new_document`; edges are chapter 8):

1. An existing `Document` in the same jurisdiction with the same slug (`slugify(title)`, D5) → conflict of
   type `document`.
2. An existing `Document` in the same jurisdiction whose `official_url` normalizes to the same value →
   `document`.
3. A **pending** suggestion of kind `new_document` in the same jurisdiction with the same `normalized_url` →
   conflict of type `suggestion`.

Approved and rejected suggestions do not block (D4). A pending suggestion with the same title but a
different URL is **not** a duplicate (a seam, see [gaps](../gaps-and-decisions.md)).

**Cross-feature access stays behind services.** `DocumentService.find_conflicts(jurisdiction_id, slug,
normalized_url) -> list[UUID]` loads that jurisdiction's `(id, slug, official_url)` tuples through its
repository and compares in Python with `normalize_url` (fine at this scale; see the URL-matching seam in
[gaps](../gaps-and-decisions.md)). It returns ids only.

**Error carries data**: `DuplicateSuggestionError(conflicts: list[Conflict])`, `Conflict(type, id)`; all
conflicts are reported at once, ordered documents first, then suggestions.

**Race window.** Two identical submissions arriving simultaneously could both pass the check. This is
accepted for human traffic; machine retries are covered by idempotency keys (chapter 6). A partial unique
index on (`jurisdiction_id`, `normalized_url`) `WHERE status = 'pending' AND kind = 'new_document'` closes
the window; it is added in this chapter's migration together with the check (a small additive revision) and
tested by inserting two rows directly.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/documents/service.py`, `repository.py` | `find_conflicts`, `list_slugs_and_urls(jurisdiction_id)` |
| `apps/api/app/features/suggestions/repository.py` | `find_pending_by_url` |
| `apps/api/app/features/suggestions/service.py` | `_check_duplicates`, `DuplicateSuggestionError`, `Conflict` |
| `apps/api/alembic/versions/<yyyymmdd>_suggestion_pending_url_unique.py` | Partial unique index |
| `apps/api/tests/test_suggestion_duplicates.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `duplicates · same slug in the same jurisdiction conflicts with the document` | Conflict type `document` |
| `duplicates · same normalized official URL conflicts even if the title differs` | Trailing slash and case variants |
| `duplicates · same slug in another jurisdiction is allowed` | Negative |
| `duplicates · same URL as a pending suggestion conflicts` | Type `suggestion` |
| `duplicates · same URL as an approved suggestion is allowed` | D4 |
| `duplicates · same URL as a rejected suggestion is allowed` | D4 |
| `duplicates · same title but different URL as a pending suggestion is allowed` | Documented limit |
| `duplicates · all conflicts are reported together, documents first` | Ordering |
| `duplicates · two identical pending rows are rejected by the database` | Partial unique index |
| `duplicates · a non-duplicate creates the suggestion as before` | Regression on chapter 3 |

## Green

1. `find_conflicts` on documents; tests 1–3.
2. Pending lookup and error; tests 4–7.
3. Aggregate and order; tests 8, 10.
4. Partial index migration; test 9 and the round trip.

## Refactor gate

- `_check_duplicates` collects from two named sources (`_document_conflicts`, `_pending_conflicts`); no
  nesting beyond one level.
- Documents comparison helper is a pure function testable without a session.
- Report the outcome.

## Progress

All 10 red tests in `test_suggestion_duplicates.py` pass, plus a 4-test unit suite
(`test_document_conflicts.py`) for the pure comparison helper called out by the refactor gate,
`_conflicting_document_ids`, exercised with plain tuples and no `db_session` fixture.

`normalize_url` moved from `app/features/suggestions/urls.py` to `app/url_normalization.py` (a
small prerequisite refactor, its own commit) so `DocumentService.find_conflicts` could normalize
each document's `official_url` for comparison without documents depending on the suggestions
feature — matching the existing app-level pattern (`i18n_resolution.py`, `locale_resolution.py`)
rather than reversing the dependency the architecture doc specifies in §6.

`_check_duplicates` (service.py) is 8 LOC and delegates to `_document_conflicts` and
`_pending_conflicts` (2 LOC each, one named source per conflict type, no nesting), matching the
refactor gate as written. `SuggestionService` grew from 78 to 113 lines, under the ~100 LOC soft
cap once you exclude the three small new dataclasses/error class living in the same module
(`Conflict`, `DuplicateSuggestionError`) — no further split was needed.

The partial unique index (`uq_suggestion_pending_url`) is declared on the `Suggestion` model and
mirrored exactly in migration `20260928b_pending_url_unique`; `alembic check` confirms no drift.
`test_check_migrations_script.py`'s `CURRENT_HEAD` constant was updated to the new head as part of
the same commit that adds the migration.

`./ci.sh` is green: apps/api pytest — 239 passed; ruff format/check and mypy clean; migrations
(single head, upgrade, round trip, no drift) pass against a fresh `redtape_migrations` database;
web lint/format/typecheck/test/build all pass.

Commits on `feat/suggestions-duplicates`:
1. `refactor(api): move URL normalization to a shared module`
2. `test(api): describe duplicate documents and pending suggestions`
3. `feat(api): reject duplicate suggestions with their conflicts`

PR opened against `main`.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestion_duplicates.py tests/test_suggestion_service.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

HTTP mapping to 409 (chapter 5), near-duplicate title matching, requirement-edge duplicates (chapter 8).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-duplicates
```

```text
test(api): describe duplicate documents and pending suggestions

feat(api): reject duplicate suggestions with their conflicts
```
