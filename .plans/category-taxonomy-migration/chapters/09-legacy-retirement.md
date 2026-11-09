---
name: "Chapter 9 — Legacy taxonomy retirement"
overview: "Retire the old domain/life-situation axes and dormant matrix aggregation only after all category parity, compatibility, and provenance gates pass."
id: C9
depends_on:
  - C8
touches:
  - apps/api/app/models/taxonomy.py
  - apps/api/app/models/document.py
  - apps/api/app/features/taxonomy/
  - apps/api/app/features/documents/
  - apps/api/app/features/candidates/
  - apps/api/app/features/discovery/
  - apps/api/alembic/versions/
  - apps/api/tests/
  - apps/web/src/features/taxonomy/
  - apps/web/src/features/documents/
  - apps/web/src/features/candidates/
  - apps/web/src/test/contract/
  - docs/
  - .plans/
execution: chapter-implementer
todos:
  - id: reference-scan
    content: "Prove no active runtime, worker, frontend, contract, migration, or documentation consumer requires the old axes."
    status: complete
  - id: api-retirement
    content: "Remove dormant matrix and legacy taxonomy routes/fields after the compatibility cutoff."
    status: complete
  - id: data-retirement
    content: "Archive/drop legacy tables and links in a separately reviewed migration with backup and rollback evidence."
    status: partial
  - id: tests
    content: "Add no-reference, migration, contract, and post-cutover compatibility tests."
    status: complete
---

# Chapter 9 — Legacy taxonomy retirement

**Repo:** `redtape` (`apps/api`, `apps/web`, docs)
**Depends on:** chapters [1–8](../01-rollout.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Remove the obsolete domain/life-situation implementation only after the category tree is the sole active contract. Retire:

- old taxonomy models and link tables;
- old document/candidate filter fields;
- old machine and public axis routes after compatibility expiry;
- dormant matrix aggregation and tests;
- unused frontend axis hooks, types, URL helpers, and translations.

Keep canonical categories, confidence, PVOG external classifications, discovery mention provenance, entity/claim data, and document requirements.

## Design decisions

- Run a repository-wide reference scan before writing the cleanup migration. A string search alone is insufficient; inspect imports, OpenAPI, generated contracts, scripts, fixtures, and operator docs.
- Expire legacy URL/API compatibility explicitly. Old links must either redirect/translate during the window or return a documented validation response after it; they must not silently become unfiltered.
- Treat dropping old tables as a forward-only release action unless a backup/restore procedure is proven. The migration must state what downgrade can and cannot restore.
- Retain historical mapping/crosswalk artifacts even after old tables are removed.
- Remove `/matrix` backend aggregation only after route, schema, client, test, and documentation references are absent. The frontend matrix is already gone.
- Do not remove internal score/completeness storage solely because public presentation was removed in chapter 7; remove only dead storage with a separate usage proof.

## Files

| Path | Change |
| --- | --- |
| `apps/api/alembic/versions/<new>_retire_legacy_taxonomy.py` | Drop/archive old axis tables, old link tables, obsolete columns, and matrix-only indexes in dependency order. |
| `apps/api/app/models/taxonomy.py` | Remove old model/link exports only after migration and all imports are updated. |
| `apps/api/app/models/document.py` | Remove legacy relationships and keep only canonical category/external-classification relationships. |
| `apps/api/app/features/taxonomy/controller.py` | Remove deprecated axis and matrix routes after compatibility cutoff. |
| `apps/api/app/features/taxonomy/service.py` | Remove legacy resolvers and matrix assembly after no caller scan. |
| `apps/api/app/schema/taxonomy/read.py` | Remove matrix/axis response types and stale machine fields. |
| `apps/api/app/features/documents/` | Remove old filter aliases, axis joins, and dead tag mapping. |
| `apps/api/app/features/candidates/` | Remove old axis filters and public tag projections. |
| `apps/api/app/features/discovery/` | Remove legacy compatibility validators only after worker rollout evidence. |
| `apps/api/tests/test_matrix_endpoint.py` and taxonomy axis tests | Delete or replace with category contract tests at the cutoff. |
| `apps/web/src/features/taxonomy/` | Remove old axis hooks/services/types after category clients own all consumers. |
| `apps/web/src/features/documents/` | Remove `groupSelection`, `situationCodes`, axis params, and dead filter components. |
| `apps/web/src/test/contract/` | Remove obsolete matrix/axis schemas and keep category contract assertions. |
| `docs/` and `.plans/` | Remove active instructions that describe the old matrix; retain historical plan links where useful. |

## Red tests

### Happy path

- `cutover · category-only document and candidate queries remain available` asserts normal browse/search behavior after legacy cleanup.
- `migration · target category and external provenance survive old-table retirement` asserts data still resolves through canonical links.
- `matrix retirement · no route or schema is registered` asserts the dormant endpoint is gone after the reference gate.

### Negative path

- `reference scan · active code cannot import legacy axis models` asserts no runtime consumer remains.
- `cutover · expired domain/situation input returns the documented error` asserts no silent unfiltered response.
- `migration · rollback limitation is explicit` asserts downgrade behavior does not claim to restore dropped data without backup.
- `provenance · retiring product taxonomy does not delete PVOG/entity/claim data` asserts source facts remain.

## Green

1. Produce and review the reference scan and parity report.
2. Expire compatibility in a release boundary with explicit URL/API behavior.
3. Remove runtime routes, schemas, clients, and dead frontend axis code.
4. Apply the cleanup migration only after backup and row-count evidence is recorded.
5. Run the full category contract and application CI.

## Refactor gate

Audit the entire legacy-removal surface:

- no compatibility branch remains inside canonical category paths;
- matrix aggregation is not retained as dead service/repository code;
- no old type is kept only because a test fixture was not updated;
- migration dependencies and downgrade limitations are documented;
- canonical category and external provenance are not coupled to the deleted tables;
- documentation uses one current vocabulary.

Report the refactor outcome and rerun the full reference scan after each deletion batch.

## Verification

```bash
cd apps/api
uv run pytest tests/test_taxonomy_api.py tests/test_taxonomy_repository.py \
  tests/test_documents_filter.py tests/test_candidates_public_api.py
alembic upgrade head
alembic check
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts

cd ../web
npm test -- src/features/taxonomy src/features/documents src/features/candidates
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

Record the reference scan, cleanup migration, compatibility expiry, backup, and post-cutover counts in [../run-ledger.md](../run-ledger.md).

## Out of scope

Reclassifying documents after the approved backfill, changing category labels, removing PVOG source facts, deleting discovery entities/claims, embeddings, entity identification, or unrelated dead-code cleanup.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b feat/retire-legacy-taxonomy
```

```text
test(api): prove legacy taxonomy has no active consumers
chore(api): retire legacy matrix taxonomy
```
