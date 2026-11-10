---
name: "Chapter 3 — Search schema"
overview: "Add the search text, embedding and embedding task tables with GIN and HNSW indexes in one migration, keyed so entity resolution and per-locale text can be added later without a schema change."
id: C3
depends_on:
  - C1
touches:
  - apps/api/app/models/
  - apps/api/alembic/versions/
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: models
    content: "Add CandidateSearchText, CandidateEmbedding and EmbeddingTask models."
    status: pending
  - id: migration
    content: "Create extensions, tables, GIN and HNSW indexes and the open-task unique index in one migration."
    status: pending
  - id: migration-gate
    content: "Make alembic check and check_migrations.sh pass with the Vector type and HNSW index."
    status: pending
  - id: tests
    content: "Add model, constraint, index and size tests."
    status: pending
---

# Chapter 3 — Search schema

**Repo:** `redtape` (`apps/api`)
**Depends on:** [Chapter 1](01-infra-and-embedding-probe.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Persist what search needs: per-candidate search text with full-text vectors, one embedding per candidate and model, and a queue of embedding tasks. Nothing reads these tables yet.

## Design decisions

- Models live in `apps/api/app/models/search.py` (one module, about 100 lines, split if it grows) and are exported from `app/models/__init__.py` so `alembic/env.py` and `create_all` see them.
- `candidate_search_text(candidate_id FK→discovery_document_candidate ON DELETE CASCADE, locale String(16), text Text, tsv_native tsvector, tsv_simple tsvector, content_hash String(64), updated_at timestamptz)`, primary key `(candidate_id, locale)`. `tsv_native` is built with the text-search configuration for the row's locale (`german` for `de`; see chapter 4's `TS_CONFIG_BY_LOCALE`), `tsv_simple` with `simple`. GIN indexes on both vectors. The tsvectors are ordinary columns written by the builder (chapter 4), not generated columns, because `unaccent()` is not immutable.
- `candidate_embedding(candidate_id FK ON DELETE CASCADE, model String(100), locale String(16), dim Integer, text_hash String(64), embedding Vector(EMBEDDING_DIM), created_at timestamptz)`, primary key `(candidate_id, model, locale)`. Chapter 16 adds one row per translated locale, so the table is sized for up to seven rows per candidate. HNSW index `USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)` (`halfvec_cosine_ops` if the chapter 1 decision chose `halfvec`). `locale` holds the canonical text's locale code, `de` today (documented as a constant on the model); per-locale vectors can be added later as extra rows without a schema change.
- `embedding_task(id uuid PK, candidate_id FK ON DELETE CASCADE, model, locale, text_hash, status enum(pending|claimed|completed|failed), priority int default 100, attempt_count int default 0, not_before, claimed_at, claimed_by_api_key_id FK api_key ON DELETE SET NULL, lease_expires_at, last_error Text, created_at, updated_at)`. Partial unique index on `(candidate_id, model, locale)` where `status in ('pending','claimed')`; index `(status, priority, created_at)` as on `discovery_task`. Native enum named `work_task_status` (generic, so chapter 13's translation tasks reuse it), values via `enum_values` like the existing discovery enums.
- The vector type and dimension (`vector(N)` or `halfvec(N)`) come from the chapter 1 decision (`EMBEDDING_DIM`); the migration hardcodes the literal number (migrations are frozen snapshots and do not import app settings), and a model test asserts the model and migration agree.
- The migration `CREATE EXTENSION IF NOT EXISTS vector` and `unaccent`. On Supabase the extension must already be enabled (operator action, rollout); the migration fails loudly if it cannot be created.
- Migration id follows the convention `YYYYMMDD_search_schema`, a single head after `20261105_retire_legacy_taxonomy` (or the then-current head).
- `scripts/check_migrations.sh` (single head, upgrade, downgrade −1, upgrade, `alembic check`) must pass; if autogenerate drift is reported for `Vector` or HNSW, add the minimal `env.py` rendering/compare hook rather than suppressing `alembic check`.
- Downgrade drops indexes, tables, the enum; it does not drop the extensions.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/search.py` | The three models and the status enum. |
| `apps/api/app/models/__init__.py` | Export them. |
| `apps/api/alembic/versions/YYYYMMDD_search_schema.py` | Extensions, tables, indexes. |
| `apps/api/alembic/env.py` | Only if needed for `alembic check` with `Vector`. |
| `apps/api/tests/test_search_models.py` | Round trips and constraints. |
| `apps/api/tests/test_search_migration.py` | Index and extension presence on a migrated database. |

## Red tests

### Happy path

- `search text · stores a de row with both tsvectors and finds it by tsquery` asserts a GIN-backed `@@` match.
- `embedding · stores a vector and orders by cosine distance` asserts nearest-first ordering for three known vectors.
- `embedding task · enqueues one pending task per candidate, model and locale` and a completed one does not block a new pending one.
- `migration · upgrade, downgrade and upgrade round trip` asserts the HNSW and GIN indexes exist (`pg_indexes`).

### Negative path

- `embedding · rejects a vector of the wrong dimension`.
- `embedding task · a second open task for the same candidate and model is refused` (unique violation).
- `candidate delete · cascades to search text, embeddings and tasks`.
- `search text · duplicate (candidate, locale) is refused`.

## Green

1. Add models and make the model tests pass on `create_all`.
2. Write the migration and run `check_migrations.sh`.
3. Record table and index sizes at the current row count (extrapolate from a fixture of 4000 rows).

## Refactor gate

- Models carry docstrings and typed columns; no `Any`.
- The status enum reuses the repository's `enum_values` helper and naming.
- No application logic in migrations; the migration imports nothing from `app`.
- The model and migration agree on dimension, index names and enum values (tested).

## Verification

```bash
cd apps/api
uv run pytest tests/test_search_models.py tests/test_search_migration.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
bash scripts/check_migrations.sh
cd ../.. && ./ci.sh
```

Record the migration id, the round-trip result, `alembic check` output, and estimated table/index sizes in [../run-ledger.md](../run-ledger.md).

## Out of scope

Writing any row (chapter 4), the machine API (chapter 5), queries (chapter 8), the translation tables (chapter 13), aliases, entity tables.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/search-schema
```

```text
test(api): describe search text, embedding and task tables
feat(api): add search schema with GIN and HNSW indexes
```
