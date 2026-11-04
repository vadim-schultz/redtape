---
name: "Chapter 2 — Category schema and data migration"
overview: "Add the self-referential category schema, preserve external classifications, and backfill document links from both legacy axes without data loss."
depends_on:
  - 01-pvog-taxonomy-contract
touches:
  - apps/api/app/models/taxonomy.py
  - apps/api/app/models/document.py
  - apps/api/app/models/discovery/
  - apps/api/app/features/documents/
  - apps/api/alembic/versions/
  - apps/api/scripts/seed_data/
  - apps/api/scripts/
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: target-model
    content: "Add category, document-category, and external-classification persistence with confidence and source provenance."
    status: pending
  - id: migration
    content: "Write reversible schema migrations in dependency order while retaining legacy tables."
    status: pending
  - id: backfill
    content: "Implement an idempotent crosswalk backfill with conflict, orphan, and count reporting."
    status: pending
  - id: tests
    content: "Add model, migration, backfill, confidence, and rollback/parity tests."
    status: pending
---

# Chapter 2 — Category schema and data migration

**Repo:** `redtape` (`apps/api`)
**Depends on:** [Chapter 1](01-pvog-taxonomy-contract.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Add the target category persistence beside the current taxonomy, seed the frozen inventory, and backfill documents and source classifications through the approved crosswalk. Existing tables remain readable until chapter 9.

The migration must be safe to rerun, report all unmapped/ambiguous rows, preserve confidence and PVOG provenance, and provide a documented rollback boundary. It must never delete old links as part of the initial backfill.

## Design decisions

- `category` is a self-referential table with a nullable root `parent_id`; active subcategories have one active parent.
- `document_category` is the only target browse relation and carries persisted confidence.
- PVOG leaves are stored in a separate external-classification relation or the equivalent generalized source table, not as category rows.
- The old link tables remain during dual-write/dual-read. The migration creates a deterministic crosswalk report keyed by old code and target category code.
- Mapping multiple old rows to one category uses the score-combination rule settled in `gaps-and-decisions.md`; it is applied consistently and recorded in the backfill report.
- Backfill is idempotent by stable category IDs and unique link keys. Rerunning it updates the intended projection rather than duplicating rows.
- A database migration must not call a live PVOG endpoint or depend on an LLM. The frozen artifact is the only taxonomy input.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/taxonomy.py` | Add `Category`, `document_category`, and external-classification models/tables; retain legacy models during the transition. |
| `apps/api/app/models/document.py` | Add the canonical category relationship without removing old relationships yet. |
| `apps/api/app/models/discovery/` | Add category/source persistence only where the existing candidate model needs a durable external classification. |
| `apps/api/alembic/versions/<new>_category_taxonomy.py` | Create target tables, constraints, indexes, and cycle-safe parent relations. |
| `apps/api/alembic/versions/<new>_category_backfill.py` | Backfill seed rows, document links, and external classifications, or call a tested idempotent backfill function. |
| `apps/api/scripts/seed_data/taxonomy.py` | Consume the chapter 1 inventory and mapping artifact. |
| `apps/api/scripts/seed_taxonomy.py` | Seed roots/children and source mappings atomically and idempotently. |
| `apps/api/scripts/<category_backfill>.py` | Provide a repeatable operator command with dry-run counts and conflict output. |
| `apps/api/app/features/documents/repository.py` | Add target link writes/reads and preserve existing confidence semantics. |
| `apps/api/app/features/documents/promotion.py` | Add the category-code promotion path while keeping the legacy path during dual-write. |
| `apps/api/tests/test_taxonomy_models.py` | Test parent, code, uniqueness, cycle, and cascade behavior. |
| `apps/api/tests/test_category_backfill.py` | Test mapping, idempotency, conflicts, external classification, and count reports. |
| `apps/api/tests/test_check_migrations_script.py` | Pin the new migration head only when the repository's migration check requires it. |

## Red tests

### Happy path

- `category · seeds roots and children with stable IDs` asserts every child resolves to its declared root and rerunning the seed updates rows in place.
- `backfill · maps old links to canonical links with confidence` asserts a document's target categories and scores equal the approved crosswalk projection.
- `backfill · preserves PVOG external classifications` asserts raw leaf/source metadata survives independently of the product category link.

### Negative path

- `category · duplicate code, missing parent, or cycle is rejected` asserts invalid taxonomy cannot be committed.
- `backfill · ambiguous mapping is reported without silent link loss` asserts the command records the row and leaves the old projection intact until policy resolves it.
- `backfill · rerun does not duplicate links or classifications` asserts unique constraints and idempotency.

Confirm failures before schema implementation. Migration tests must run against the supported Postgres environment; SQLite-only tests are not sufficient for Postgres constraints.

## Green

1. Create the target tables and constraints with legacy tables untouched.
2. Seed the frozen category tree and verify deterministic IDs.
3. Implement the dry-run/reporting backfill and test it on fixtures with direct, duplicate, ambiguous, unmapped, and PVOG-backed rows.
4. Execute the target backfill in a transaction or bounded repeatable batches, preserving old links until parity is accepted.
5. Add dual-write hooks at document promotion and document/category repository boundaries.

## Refactor gate

Audit the entire taxonomy model and backfill unit:

- parent validation is a named tree validator, not duplicated in seed and migration code;
- backfill transformation, persistence, reporting, and rollback are separate units;
- no boolean parameter selects legacy versus target behavior deep inside repositories;
- old-to-new field tuples are centralized in one mapping DTO;
- migrations are deterministic, bounded, and do not import live clients;
- constraints cover every mapping invariant that the database can enforce;
- repository methods do not mix source metadata transformation with SQL assembly.

Report the refactor outcome and rerun model/backfill tests after every extraction.

## Verification

```bash
cd apps/api
uv run pytest tests/test_taxonomy_models.py tests/test_category_backfill.py
alembic upgrade head
alembic downgrade <pre-category-revision>
alembic upgrade head
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
./ci.sh
```

Run the backfill in dry-run mode and record before/after counts, conflict count, null confidence count, and PVOG external-classification count in [../run-ledger.md](../run-ledger.md).

## Out of scope

Replacing public filters, deleting legacy tables, changing LLM/PVOG payloads, frontend work, embeddings, entity identification, and any data cleanup unrelated to taxonomy.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b feat/category-schema-data-migration
```

```text
test(api): describe canonical category persistence and backfill
feat(api): add category schema and idempotent taxonomy backfill
```
