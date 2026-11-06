---
name: "Chapter 10 — Docs sync and live validation"
overview: "Synchronize category migration documentation and record read-only post-deploy evidence for taxonomy, search, chips, hidden technical metadata, accordions, sources, and PVOG provenance."
id: C10
depends_on:
  - C9
touches:
  - docs/
  - .plans/
  - apps/api/tests/
  - apps/web/src/
  - .github/
execution: chief-of-staff
todos:
  - id: docs-sync
    content: "Remove stale active matrix/domain/life-situation instructions and document the canonical category and provenance boundaries."
    status: complete
  - id: static-validation
    content: "Run link, contract, translation, and reference checks after cleanup."
    status: complete
  - id: live-validation
    content: "Record read-only post-deploy category, UI, PVOG, and data-parity observations."
    status: complete
  - id: follow-up
    content: "Record any unresolved mapping, source, or compatibility issues without changing production data from the validation run."
    status: complete
---

# Chapter 10 — Docs sync and live validation

**Repo:** `redtape` (docs and read-only validation)
**Depends on:** [Chapter 9](09-legacy-retirement.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)

## Goal

Make the repository documentation describe the category tree as the current product contract and record evidence that the deployed system behaves accordingly. This chapter does not silently repair data or change production configuration.

## Documentation scope

Update active references in:

- [docs/planning/directions/data-model-migrations/02-documents-and-requirements.md](../../../docs/planning/directions/data-model-migrations/02-documents-and-requirements.md);
- [docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md);
- [docs/operations/candidate-view.md](../../../docs/operations/candidate-view.md);
- [docs/operations/discovery-layer.md](../../../docs/operations/discovery-layer.md);
- [docs/planning/00-master-summary.md](../../../docs/planning/00-master-summary.md);
- related taxonomy, discovery, migration, and frontend plan pointers found by the reference scan.

Keep historical matrix plans as historical records where useful. Mark them as superseded rather than rewriting their shipped decisions. Active docs must state:

- category roots/subcategories are the user-facing taxonomy;
- PVOG identifiers are source classifications;
- search is primary and category browse is secondary;
- category chips are red canonical links;
- staging/completeness internals are not user-facing;
- the document detail sections are five accordions with the requested defaults;
- source cards are subordinate source evidence;
- embeddings and entity identification are future, separate capabilities.

## Read-only validation

### Taxonomy and data

- `GET /api/v1/categories` returns the frozen localized tree.
- The machine vocabulary digest matches the deployed inventory.
- Every active subcategory has one parent and no cycle.
- Document/category counts match the approved migration report.
- Source/PVOG external-classification counts do not regress.
- Documents without categories remain searchable.

### API behavior

- Root filtering includes descendants.
- Subcategory filtering targets the exact category.
- Unknown category returns the documented validation error.
- Old query parameters behave according to the compatibility cutoff.
- `/matrix` is absent after retirement.

### Web behavior

- Search appears before category browsing.
- Root and subcategory chips use the red semantic token and XS presentation.
- Chip links reach the same category-filtered document list as front-page selection.
- No chip is nested inside another interactive element.
- The document view does not show staged/unreviewed or completeness copy.
- The progress circle remains visible where specified.
- All five accordion items exist; ingress, egress, and flow start expanded; evidence and sources start collapsed.
- Sources render one subordinate card per source, with valid external links where available.

### Ingest and provenance

- New PVOG records retain source leaf/path/version metadata.
- Category mapping uses the frozen crosswalk.
- LLM and manual category codes match the machine vocabulary.
- Unknown/stale codes are reported rather than silently converted.

## Red/green evidence pairs

This chapter is primarily documentation and validation, not a production feature. Use evidence pairs instead of adding new product tests:

- **Expected:** the reference scan finds no active legacy taxonomy dependency. **Failure:** any active import, route, schema, translation, or operator instruction still relies on an obsolete axis.
- **Expected:** a deployed root chip reaches descendant-inclusive filtered results. **Failure:** chip href and front-page filter resolve to different result sets.
- **Expected:** the document detail hides technical staging/completeness text while confidence remains visible. **Failure:** either disclosure reappears or the progress circle disappears.
- **Expected:** accordion/source behavior matches the contract. **Failure:** default expansion, keyboard behavior, or source-card count differs.

Record commands, timestamps, deployment version, observations, and follow-up links in [../run-ledger.md](../run-ledger.md).

## Refactor gate

Audit the documentation and validation artifacts:

- active docs use one current taxonomy vocabulary;
- historical documents are linked as historical rather than presented as current contracts;
- validation checks are read-only and repeatable;
- no live check embeds credentials or mutates production;
- evidence maps to an invariant or decision, not a screenshot-only claim;
- unresolved gaps have an owner/follow-up plan.

Report `Refactor gate: smells found -> ...; refactorings applied -> ...` or `no refactor needed`.

## Verification

```bash
./ci.sh
```

Additionally run the repository's documented link checker, OpenAPI/frontend contract tests, translation parity tests, and a repository reference scan for `domain`, `life_situation`, `matrix`, `Staged and unreviewed`, and `completeness`. Use the exact commands supported by the current CI configuration and record their output summaries in the ledger.

## Out of scope

Production writes, automatic reclassification, PVOG crawl execution as a substitute for a reviewed mapping, embedding generation, entity identification, and unrelated documentation cleanup.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b docs/category-taxonomy-validation
```

```text
docs: document canonical category migration and validation
```
