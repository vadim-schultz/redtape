---
name: "Chapter 8 — Remove seeded documents"
overview: "Stop seeding the four MVP documents and three requirements, delete exactly those rows from existing databases with a data migration, and keep the seeded jurisdictions and the taxonomy."
todos:
  - id: split-seed
    content: "Rename seed_documents.py to seed_jurisdictions.py, keep ID_DE/SN/DD and jurisdiction upserts, drop documents and requirements"
    status: pending
  - id: taxonomy-seed
    content: "seed_taxonomy and seed_data/taxonomy drop DOCUMENT_TAGS and the document link paths"
    status: pending
  - id: migration
    content: "Alembic data migration deleting only the four stable document ids and three requirement ids"
    status: pending
  - id: start-sh
    content: "start.sh calls seed_jurisdictions, not seed_documents"
    status: pending
  - id: tests-docs
    content: "Migration tests, ported seed tests, heads bumped, ops docs updated"
    status: pending
isProject: false
---

# Chapter 8 — Remove seeded documents

**Repo:** `redtape` (`apps/api`, ops docs) · **Branch:** `feat/document-browse-confidence-remove-seeded-documents` · **Status:** planned
**Depends on:** Chapter 7 (the UI no longer reads `document`) · **Architecture:** [../00-architecture.md](../00-architecture.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Decision:** [D6](../gaps-and-decisions.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

The catalogue is real data from the database. The sample documents must not reappear, so the seed stops creating them, and the rows already in any database are deleted. Paths under `apps/api/`.

## Facts (read 2026-11-02, re-verify at implementation time)

- `scripts/seed_documents.py` upserts the DE, SN and DD jurisdictions (`ID_DE/SN/DD = 11111111-…1101/1102/1103`), four documents (`ID_DOC_MELDE/AUSWEIS/GEBURT/WOHN = 22222222-…2201–2204`) and three requirements (`ID_REQ_1–3 = 33333333-…3301–3303`).
- `scripts/start.sh` runs it on **every boot**, so deleting rows alone would bring them back on the next deploy.
- `scripts/seed_data/taxonomy.py` imports the four `ID_DOC_*` ids and tags those documents in `DOCUMENT_TAGS`; `scripts/seed_taxonomy.py` writes the links.
- `document_domain`, `document_life_situation` and `document_requirement` reference `document.id` with `ON DELETE CASCADE`; `document.jurisdiction_id` is `RESTRICT`, so jurisdictions are not deleted.
- Importers of the seed module: `tests/test_print_federal_jurisdiction_id.py` (`ID_DE`), `tests/test_seed_taxonomy.py` (`ID_DOC_GEBURT`, `seed_mvp_graph`), `tests/test_seed_documents.py`, `scripts/seed_data/taxonomy.py`.
- Current Alembic head: `20261102_pvog_leaf_code`; the head is pinned in `tests/test_check_migrations_script.py:21` (`CURRENT_HEAD`) and `tests/test_discovery_staging_migration_retry.py:19` (`HEAD_REVISION`).

## Design

1. **Split the seed.** Rename `scripts/seed_documents.py` → `scripts/seed_jurisdictions.py` (`git mv`, keeping history). Keep `ID_DE/SN/DD`, `_find_or_create_jurisdiction` and the jurisdiction upserts; delete `_upsert_documents`, `_upsert_requirements`, the `ID_DOC_*` and `ID_REQ_*` constants and the `Document`/`DocumentRequirement` imports. Rename the entry point `seed_mvp_graph` → `seed_jurisdictions`, update the docstring and the final `print`. Update every importer listed above, `scripts/print_federal_jurisdiction_id.py` if it imports the module, and `scripts/fix_saxony_jurisdiction_leak.py` comments.
2. **Taxonomy seed.** Remove `DOCUMENT_TAGS`, its `ID_DOC_*` import in `seed_data/taxonomy.py`, and in `seed_taxonomy.py` the document-link path (`_link` on `document_*` tables, `_validate_tags` for document tags) and the `document_domain`/`document_life_situation` imports if now unused. Domains, situations, groups and `SITUATION_GROUP_CODES` stay.
3. **`scripts/start.sh`.** Replace `python -m scripts.seed_documents` with `python -m scripts.seed_jurisdictions`; update the comment that mentions it. `alembic upgrade head` (line 1) already runs before the seeds, so the deletion migration lands before the next boot's seed.
4. **Data migration** `alembic/versions/<date>_remove_seeded_documents.py` (naming and docstring per the existing files: Revision ID, Revises, Create Date, rationale), `down_revision = "20261102_pvog_leaf_code"` (use the head at implementation time). `upgrade()` runs:
   ```sql
   DELETE FROM document_requirement WHERE id IN (<3 ids>) OR parent_document_id IN (<4 ids>) OR required_document_id IN (<4 ids>);
   DELETE FROM document WHERE id IN (<4 ids>);
   ```
   Link rows go by `ON DELETE CASCADE`. Only the exact stable ids are touched: a promoted or user-created document, even with the same slug, is never deleted by id mismatch. `downgrade()` is a documented no-op ("irreversible: seeded sample data, removal approved in D6"). `scripts/check_migrations.sh` must still pass (single head, upgrade, downgrade -1 and upgrade, `alembic check` for drift — a data-only migration changes no model).
5. **Docs here** (the rest in chapter 10): `docs/operations/deployment-checklist.md:32-33` and `:177-178` ("expected 4 documents seeded"), `docs/operations/local-development.md:29,115-129`, `apps/api/README.md:14,49,71`, `docs/operations/openplz-import.md:68`, `docs/operations/discovery-layer.md:40,351`, `docs/operations/discovery-online.md:359` — replace `seed_documents` with `seed_jurisdictions` and drop the seeded-documents claims. Keep `tests/test_deployment_checklist.py` and `tests/test_discovery_docs_sync.py` green.

## Tests

Happy path:
- `tests/test_remove_seeded_documents_migration.py`: with the four seeded documents, their tag links and three requirements present, `upgrade()` removes all of them.
- `tests/test_seed_jurisdictions.py` (ported from `test_seed_documents.py`): the three "reuses an existing … row instead of duplicating it" tests keep their assertions against `seed_jurisdictions`; running the seed twice is idempotent.
- `tests/test_seed_taxonomy.py`: terms and groups are seeded; no document is created or tagged.

Negative path:
- A non-seed document (another id, even the same slug) with tags and a requirement edge **survives** the migration untouched.
- Running the migration on a database with none of the rows is a no-op, not an error.
- `seed_jurisdictions` does not create any `document` or `document_requirement` row.

Bump `CURRENT_HEAD` and `HEAD_REVISION` to the new revision id.

## Verification

```bash
cd apps/api && uv run pytest tests/test_remove_seeded_documents_migration.py tests/test_seed_jurisdictions.py tests/test_seed_taxonomy.py tests/test_check_migrations_script.py tests/test_discovery_staging_migration_retry.py tests/test_print_federal_jurisdiction_id.py
./ci.sh                                              # includes scripts/check_migrations.sh and the docs-sync tests
```

**Production effect (not a manual step):** the migration runs through `start.sh` on the next deploy and deletes the four documents. Chapter 11 confirms `GET /api/v1/documents` returns `total: 0` and the DE/SN/DD jurisdictions still exist.

## Data-design gate

Applies (a migration). Record: the delete is idempotent and id-scoped; cascades are database-level; no lock concern at four rows; the rollback is intentionally a no-op and that is `accepted-risk` (S6).

## Refactor gate

Scan `seed_jurisdictions.py` and `seed_taxonomy.py` (dead imports and constants after the split; Mysterious Name `seed_mvp_graph` → `seed_jurisdictions`).

## Commits

- `refactor(api): rename seed_documents to seed_jurisdictions and stop seeding sample documents`
- `feat(api): migration removing the seeded sample documents and requirements`
- `docs: drop seeded-document references from the operator docs`

## Out of scope

Deleting the `document` table, its API or models (seam S1); deleting jurisdictions; any change to candidates.
