---
name: "Chapter 4 — Duplicate detection"
overview: "Creating a suggestion raises DuplicateSuggestionError listing conflicting documents or pending suggestions when the derived slug or the normalized official URL already exists in the same jurisdiction."
todos:
  - id: documents
    content: "DocumentService.find_conflicts (read-only)"
    status: pending
  - id: pending
    content: "SuggestionRepository.find_pending_by_url"
    status: pending
  - id: service
    content: "SuggestionService checks before insert"
    status: pending
isProject: false
---

# Chapter 4 — Duplicate detection

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-duplicates` · **Status:** planned

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
