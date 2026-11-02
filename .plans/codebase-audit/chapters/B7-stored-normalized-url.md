---
name: "Chapter B7 — Stored normalised URL (optional)"
overview: "Approved by the operator on 2026-11-02. Store Document.normalized_url, backfill it in a reversible migration, and let duplicate detection use one indexed query instead of reading every document of a jurisdiction."
todos:
  - id: approval
    content: "Operator approves the migration before any work starts (done 2026-11-02)"
    status: done
  - id: characterize
    content: "Pin find_conflicts behaviour on the unchanged scan"
    status: pending
  - id: migration
    content: "Add column + index + backfill, up and down, drift check green"
    status: pending
  - id: query
    content: "find_conflicts uses the indexed query; model keeps the column in sync"
    status: pending
isProject: false
---

# Chapter B7 — Stored normalised URL (OPTIONAL)

**Repo:** `redtape` · **Branch:** `refactor/stored-normalized-url` · **Status:** planned, **operator approved 2026-11-02**

**Depends on:** B3 (layering and guards) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (L4) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/models`, `api/alembic`, `api/features/documents`

**Findings:** L4

> **Approved.** The operator approved this migration on 2026-11-02, with the reason that a stored value is traceable. It is still the only migration in the audit. The release gate in [../01-rollout.md](../01-rollout.md) does not depend on it, so if it slips it does not block the release. Keep the migration reversible, keep the backfill idempotent, and record the revision id in the ledger.

## Goal

Duplicate detection for a new document no longer reads every document of the jurisdiction and normalises their URLs in Python. `Document` stores `normalized_url`, kept in step by the model, and the conflict check is a single indexed `SELECT`. The set of conflicts returned is identical for every input.

## Verified facts

- `DocumentService.find_conflicts` (`features/documents/service.py:163-166`; after B3 it lives in `DocumentPromotion` in `features/documents/promotion.py`) calls `DocumentRepository.list_slugs_and_urls(jurisdiction_id)` (`repository.py:197-202`), which returns `(id, slug, official_url)` for **every** document in the jurisdiction. `_conflicting_document_ids` then keeps rows whose slug equals the candidate slug, or whose `normalize_url(official_url)` equals the candidate's normalised URL (`service.py:19-32`).
- The callers run it on every create, preview and promote: `NewDocumentHandler.conflicts` and `_check_still_free` (`features/suggestions/handlers.py:90-110`).
- `Suggestion` already stores the value: `normalized_url: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)` (`models/suggestion.py:103`) and a partial unique index on `(jurisdiction_id, normalized_url)` for pending new documents. `Document` has `official_url: String(500)` but no normalised column (`models/document.py:19,31`), and `uq_document_jurisdiction_slug` is its only uniqueness rule.
- The normalisation function is `normalize_url` in `app/url_normalization.py` (lower-case scheme and host, drop fragment and `utm_*`/`fbclid`/`gclid`, sort the query, trim a trailing slash).
- Documents are created in application code at exactly one place, `DocumentService._build_document` (`service.py:137-144`, moves to `DocumentPromotion` in B3). 17 test modules construct `Document(...)` directly.
- Migration conventions (`apps/api/alembic/versions/`): file `YYYYMMDD_snake_name.py`, `revision` equal to the file stem, `down_revision` the current single head (today `20261102_remove_seeded_documents`), a docstring with `Revision ID`, `Revises`, `Create Date`, typed `upgrade()`/`downgrade()` (see `20261102_pvog_leaf_code.py`). `apps/api/scripts/check_migrations.sh` runs: single head, `upgrade head`, `downgrade -1` then `upgrade head`, `alembic check` (model/migration drift). It runs in `ci.sh:57` and in `.github/workflows/api-lint-test.yml:111`. `tests/test_check_migrations_script.py:25` pins `CURRENT_HEAD = "20261102_remove_seeded_documents"` and must be updated to the new revision.

## Design

1. **Column and index.** `Document.normalized_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)` (wider than `official_url`: re-encoding the query in `normalize_url` can lengthen a 500-character URL, and an overflow would fail the backfill) and `Index("ix_document_jurisdiction_normalized_url", "jurisdiction_id", "normalized_url")` in `__table_args__`. **Not unique**: existing data may already hold two documents with the same normalised URL, and the migration must not fail on them.
2. **Keep it in step in one place.** `@validates("official_url")` on `Document` sets `self.normalized_url = normalize_url(value) if value else None` and returns `value`. Every ORM write path (promotion and the test fixtures) is covered without touching call sites. Bulk Core `update()` statements that change `official_url` would bypass it; none exist (`grep` of `app/` and `scripts/`: only `jurisdiction_id` is updated in bulk, by `fix_saxony_jurisdiction_leak.py`).
3. **Migration** `apps/api/alembic/versions/<date>_document_normalized_url.py` (revision id = file stem; use the implementation date): `upgrade()` adds the nullable column, creates the index, then backfills in batches. The backfill uses a **frozen copy** of the normalisation function inside the migration (migrations are snapshots; importing `app.url_normalization` would change history if the rules change later) and `sa.text`/Core only, no ORM models. `downgrade()` drops the index and the column. It is reversible without data loss: the column is derived data.
4. **Query.** The repository gets `find_conflicting_document_ids(jurisdiction_id, slug, normalized_url) -> list[UUID]`: `WHERE jurisdiction_id = :j AND (slug = :s OR normalized_url = :u)`, the `normalized_url` arm omitted when the candidate has none (a URL-less candidate matches on the slug alone, as today). Result order is not part of today's contract (callers build a list and test membership), but sort by `created_at, id` for stability and say so in the docstring. `list_slugs_and_urls`, `_conflicting_document_ids` and `_same_url` are deleted once nothing uses them.
5. **Staleness policy.** If `normalize_url` changes later, stored values go stale (the same property `Suggestion.normalized_url` already has). State it in the model docstring; the remedy is a new backfill migration. Do not add an automatic rebuild job.

## Files

- `apps/api/app/models/document.py`: column, index, validator.
- New `apps/api/alembic/versions/<date>_document_normalized_url.py`.
- `apps/api/app/features/documents/repository.py`: new query, delete `list_slugs_and_urls`.
- `apps/api/app/features/documents/promotion.py` (post-B3; `service.py` if B3 has not moved it): `find_conflicts` uses the query; delete the two helper functions.
- `apps/api/tests/test_check_migrations_script.py:25`: new `CURRENT_HEAD`.
- `apps/api/tests/test_document_conflicts.py`, `test_document_repository.py`, `test_document_service.py`, `test_suggestion_duplicates.py`: see the loop.

## TDD loop

### Red

Characterise on the unchanged scan first (all green):

1. `tests/test_document_conflicts.py` already has `test_matches_on_normalized_url` for the pure function. Add DB-level characterisation in `tests/test_document_repository.py` or a new `tests/test_document_conflict_query.py`: `test_conflict_on_same_slug`, `test_conflict_on_same_normalized_url_with_tracking_params_and_trailing_slash`, `test_conflict_on_both_slug_and_url_returns_the_document_once`, and negatives `test_no_conflict_for_other_jurisdiction`, `test_url_less_candidate_matches_on_slug_only`, `test_document_without_url_never_matches_a_url`, `test_different_query_values_do_not_conflict`.
2. The suggestion-level pins stay green: `tests/test_suggestion_duplicates.py` and `tests/test_promote_new_document.py` (the `PromotionConflictError` race).

Then new red tests:

3. `test_document_sets_normalized_url_from_official_url` (also when `official_url` is reassigned, and `None` when cleared), `test_normalized_url_fits_the_column_for_a_500_char_url_whose_query_expands_on_reencoding`. Fail: no column.
4. `test_find_conflicts_issues_one_select` (statement counter as in B4; today it is one `SELECT` returning all rows, so assert the statement carries the `WHERE ... slug =` predicate and fetches only ids).
5. Migration tests (extend `tests/test_check_migrations_script.py` or add `tests/test_document_normalized_url_migration.py`, using the same isolated-database helper): `test_backfill_normalises_existing_rows` (insert rows through the previous revision with raw SQL, upgrade, assert values; rows with `official_url IS NULL` stay `NULL`), `test_backfill_matches_the_application_function_on_a_corpus` (a table of 15 representative URLs compared with `app.url_normalization.normalize_url`, which guards the frozen copy against drift today), `test_downgrade_drops_column_and_index`.

### Green

1. Model change and validator (the existing suite plus tests 3 and 4 go green with `Base.metadata.create_all`).
2. Migration; run `bash scripts/check_migrations.sh` locally against a scratch database (never the shared dev database; use a scratch `DATABASE_URL` per the project's local-dev-database rule).
3. Switch `find_conflicts` to the repository query; delete the dead helpers.

### Refactor

Gate: judge by responsibility, not line count. The repository method should be describable as "ids of documents that clash with a slug or URL"; the service layer keeps no matching logic. Check that no second normalisation call remains anywhere in `features/documents` (one frozen copy in the migration is intended and documented); no one-line wrapper between `find_conflicts` and the repository method beyond the promotion port that B3 introduced; no new `Any`; docstrings (imperative) on the new repository method and the validator; remove `D` and `ANN401` baseline entries for the files rewritten. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with rows read per call before (all documents of the jurisdiction) and after (matching ids only).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_document_conflicts.py tests/test_document_conflict_query.py tests/test_document_repository.py \
  tests/test_document_service.py tests/test_suggestion_duplicates.py tests/test_promote_new_document.py \
  tests/test_check_migrations_script.py tests/test_document_normalized_url_migration.py
bash scripts/check_migrations.sh      # against an empty scratch DATABASE_URL: single head, upgrade, round trip, alembic check
cd ../..
./ci.sh
```

Do not run the migration against the shared dev database or any shared environment from this chapter. The deploy applies it through `scripts/start.sh` (`alembic upgrade head`) on the next boot; the operator decides when.

## Parallel notes

Runs in batch 4 alongside B5 and I4 (operator approved 2026-11-02). It is `After: B3`, so `DocumentPromotion` exists. Do not touch `features/discovery/*` (B5), `apps/discovery-ingest` (I3, I5) or `features/suggestions/*` (B2 merged earlier; this chapter changes no suggestion code). Do not add a second Alembic head: if another chapter ever adds a migration, rebase this one onto it and update `CURRENT_HEAD` once. G2 (close baselines) may edit the mypy override for `app.features.documents.service`; coordinate by running after this chapter.
