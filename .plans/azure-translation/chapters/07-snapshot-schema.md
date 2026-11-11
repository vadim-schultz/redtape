---
name: "Chapter 07 — Snapshot translation schema"
overview: "Add the tables that track snapshot translations and their queue: a migration, models, and the leased-queue type that lets the existing claim, lease and settle code serve a second task table. No endpoints, worker or enqueue yet."
id: AZ07
depends_on:
  - AZ01
touches:
  - apps/api/alembic/versions/
  - apps/api/app/models/snapshot_translation.py
  - apps/api/app/models/__init__.py
  - apps/api/app/features/search/leased_queue.py
  - apps/api/app/features/translation/priority.py
  - apps/api/app/features/translation/task_repository.py
  - apps/api/tests/
execution: chapter-implementer
---

# Chapter 07 — Snapshot translation schema

**Repo:** `redtape` (`apps/api`) · **Depends on:** [Chapter 01](01-ledger-resource.md) · **Decisions:** [D1](../gaps-and-decisions.md#d1--the-document-unit-is-the-procedure-page-keyed-per-page), [D7](../gaps-and-decisions.md#d7--eager-queue-driven-translation-reads-never-translate) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Create the storage for snapshot translations: one index row per (catalogue row, locale), one queue row per open job, and the type changes that let the existing leased queue claim them. The API gains no route and the worker gains nothing in this chapter.

## Scope

- In: migration, models, the `LeasedQueue` type variable, priority and the hash-aware upsert for the new task table, tests.
- Out: routes (08), enqueue and hooks (09), the store and payload (08), the worker (11).

## Design

1. **Migration.** Revises the current Alembic head (check with `alembic heads`; the head today is `20261111_translation_schema`). Create:
   - `snapshot_translation`: primary key `(catalogue_service_id, locale)`, foreign key to `catalogue_service`. Columns: `artifact_sha256` (64), `source_hash` (64, nullable), `engine` (50), `model` (100, nullable), `storage_key` (text, nullable), `content_sha256` (64, nullable), `size_bytes` (integer, nullable), `truncated` (boolean, default false), `skipped_reason` (40, nullable), `created_at`, `updated_at`. Check constraint: `storage_key` and `skipped_reason` are not both set.
   - `snapshot_translation_task`: the same columns as `translation_task`, using the existing `work_task_status` enum with `create_type=False`. Plus `catalogue_service_id`, `locale`, `artifact_id` and `artifact_sha256`, both nullable, filled at claim time, not at enqueue. A partial unique index on `(catalogue_service_id, locale)` where the status is in `OPEN_TASK_PREDICATE`.
2. **Models** in `models/snapshot_translation.py` (one file, under 100 lines), registered in `models/__init__.py` so `alembic check` sees them.
3. **Leased queue.** `TaskT` in `features/search/leased_queue.py` gains the new model. `claim`, `owned`, `fail_owned` and `release_owned` then work unchanged, provided the column names match the existing table.
4. **Priority.** `priority.py` gets a snapshot function that mirrors the card rule: base 0 for a first translation and 10,000 for a re-translation, with the highest candidate confidence ranking first.
5. **Upsert.** `task_repository.py` gets an upsert for the snapshot task: an existing pending row gets its priority updated when the priority changes. A claimed row is left alone. A completed row is not reopened here; that is the job of chapter 09.

## Files

| Path | Change |
| --- | --- |
| `alembic/versions/20261111_snapshot_translation.py` (new, or next revision) | the two tables and indexes |
| `app/models/snapshot_translation.py` (new) | ORM models |
| `app/models/__init__.py` | import the models |
| `app/features/search/leased_queue.py` | `TaskT` includes the snapshot task |
| `app/features/translation/priority.py` | snapshot priority |
| `app/features/translation/task_repository.py` | snapshot upsert |
| `apps/api/tests/test_snapshot_*.py` (new) | migration, model, queue, priority, upsert tests |

## Red tests

**Happy path**
- `Migration · upgrade, downgrade and upgrade again round-trip; alembic check is clean`
- `Migration · the partial unique index allows one open task per (catalogue row, locale) and a new one after completion`
- `Queue · claim orders by priority, then age, for the snapshot model`
- `Queue · an expired lease is reclaimed; a task at the attempt cap is failed`
- `Priority · a first translation has base 0, a re-translation base 10,000, and higher confidence ranks earlier`
- `Upsert · a pending row's priority is updated; a claimed row is unchanged`

**Negative path**
- `Model · a row with both storage_key and skipped_reason is refused by the check constraint`
- `Model · a second open task for the same catalogue row and locale is refused`
- `Model · a status outside the work_task_status enum is refused`

## Green

Write the migration and models for the first red test, then add each behaviour in the order above.

## Refactor gate

- The snapshot model reuses the card model's column definitions through a shared mixin only if the third table appears; for two, keep the definitions explicit.
- `priority.py` gets one function per concern, not a branch per task kind.
- House rules: docstrings, no `Any`, at most 3 parameters, about 100 lines per file.

## Verification

```bash
cd apps/api
bash scripts/check_migrations.sh
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_snapshot_*.py tests/test_leased_queue*.py tests/test_translation_*.py
cd ../.. && ./ci.sh
```

## Out of scope

Routes and the store (08), enqueue and hooks (09), any data backfill (the tables start empty), the worker.

## Operator steps after merge

None. The tables are empty and no backfill runs until chapter 09 is merged and the operator runs it.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-07-snapshot-schema
# test(api): ... (red), feat(api): ... (green), refactor(api): ... (gate)
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
