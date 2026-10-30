---
name: "Chapter 9 — Catalogue versus coverage"
overview: "Make the admin catalogue and coverage pages distinct: coverage keeps the system-health summary and budgets; catalogue drops the shared summary and shows its own clickable summary chips, a Title column and a stage filter."
todos:
  - id: catalogue-api
    content: "Catalogue list gains sort_by title and filter[stage] (small API addition)"
    status: pending
  - id: catalogue-summary
    content: "Catalogue renders its typed summary (total, by source, by stage) as clickable filter chips"
    status: pending
  - id: drop-shared-summary
    content: "Catalogue no longer renders CoverageSummary or fetches coverage"
    status: pending
  - id: catalogue-columns
    content: "Title column with the bounded cell and a stage filter in the header"
    status: pending
isProject: false
---

# Chapter 9 — Catalogue versus coverage

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/candidate-view-catalogue-coverage` · **Status:** planned  
**Depends on:** [08-admin-documents-table.md](08-admin-documents-table.md) (`TruncatedText`, `Tooltip`) · **Architecture:** [../00-architecture.md](../00-architecture.md) §9 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

`/admin/discovery/catalogue` and `/admin/discovery/coverage` stop showing the same block at the top. After this chapter:

- **Coverage** is the system-health page, exactly as today: the eight-card `CoverageSummary` (catalogue rows by source, task queue, tasks by kind, document candidates, artifact storage, failed tasks by source, last successful run, extraction outcomes) and the budgets section. The owner likes this layout; it does not change.
- **Catalogue** is the browsing page: its own summary chips (total rows, rows per source, rows per pipeline stage), which are filters on the table below; a Title column; a stage filter. The layout (summary row above a table card) is kept.

Today (code read 2026-10-30): `DiscoveryCataloguePage` renders `CoveragePanel` (which wraps the same `CoverageSummary` the coverage page renders) above `CatalogueIndexPanel`; `useCatalogueState` fetches coverage and the catalogue page together; `CatalogueListResponse.summary` (`CatalogueSummaryChips`: `total`, `by_source`, `by_pipeline_stage`) is typed and returned by the API but never rendered; the table has no title column although `CatalogueServiceSummary.title_i18n` exists; the API allows `filter[source]` only.

## Design decisions

- **Distinct, not unified** (decision D13). No shared component with a mode flag; each page owns its top block. `CoverageSummary` stays exclusive to coverage.
- **Summary chips act as filters.** `CatalogueSummaryChips` renders a total chip and one chip per source and per stage with its count from `summary`. Clicking a source or stage chip sets the matching list filter (`filter[source]`, `filter[stage]`), clicking the active chip clears it, and the active chip is marked pressed (`aria-pressed`). Counts describe the **unfiltered** catalogue (that is what the API's summary returns today); this is stated in the panel's caption so a filtered table next to unfiltered counts is not confusing.
- **Title column.** A display column using `TruncatedText` (`maxWidth="28rem"`) with the localized `title_i18n`, falling back to the external id; sorting by `title` is added to the API (below). The external-id column keeps its pipeline link.
- **Stage filter.** `stage` column gets an `eq` select filter (`T0` to `T4`, labelled with the existing stage names) alongside its sort.
- **API addition (small).** `catalogue_list_query.py`: `sort_by=title` (lower-cased localized title with the existing tie-break) and `filter[stage]` (enum `T0..T4`, 422 otherwise). The default order, the `summary` shape and `q` over external id are untouched. No migration.
- **Fewer requests.** The catalogue page no longer calls the coverage endpoint; `useCatalogueState` becomes a single-query state (loading, error with retry, ready). The coverage page keeps its own queries.

## Files

**Edit**

- `apps/api/app/features/discovery/catalogue_list_query.py`, `repository/catalogue_filter.py` (title sort and stage filter), API tests beside `tests/test_discovery_admin_list_query.py`
- `apps/web/src/features/discovery-admin/containers/DiscoveryCataloguePage.tsx`, `hooks/useCatalogueState.ts`, `hooks/useCatalogueListState.ts`, `services/catalogueListQuery.ts`, `types/`
- `apps/web/src/features/discovery-admin/components/CatalogueIndexPanel.tsx`, `columns/catalogueColumns.tsx`, `CatalogueServicesTable.tsx`
- `apps/web/src/i18n/fallback/en.json` and `de.json` (`discovery_admin.catalogue.*`)

**Create**

- `apps/web/src/features/discovery-admin/components/CatalogueSummaryChips.tsx` (+ test)

**Do not edit**

- `DiscoveryCoveragePage.tsx`, `CoverageSummary.tsx`, `BudgetMeters.tsx` and the coverage card builders; the coverage endpoint; guards

## Red tests

| Test | Asserts |
| --- | --- |
| `catalogue api sorts by title and breaks ties deterministically` | API: ascending and descending title order, stable across repeated requests and pages. |
| `catalogue api filters by stage and totals the filtered result` | API: `filter[stage]=T4` returns only T4 rows and `total` matches. |
| Negative: `catalogue api rejects an unknown stage` | API: `filter[stage]=T9` is a 422 in the stable validation shape; nothing queried. |
| `catalogue page renders its own summary and not the coverage cards` | Web: the eight coverage card titles are absent; total, per-source and per-stage chips are present with the API's counts. |
| `catalogue page does not request coverage` | Web: the stub API sees no call to the coverage route from the catalogue page. |
| `source chip sets the source filter and clears on second click` | Web: click sends `filter[source]=...`, the chip is `aria-pressed`, second click removes it and resets the offset. |
| `stage chip and stage header filter agree` | Web: choosing a stage in the header filter marks the stage chip pressed. |
| `title column clips with a tooltip and falls back to the external id` | Web: a long title is clipped with full text in the tooltip; a row without a title shows its external id. |
| Negative: `catalogue error shows retry and no stale chips` | Web: a failed catalogue query shows the shared error with retry; a refetch keeps the previous rows (existing refreshing state). |
| Negative: `coverage page is unchanged` | Web: the coverage page still renders all eight cards and the budgets section (regression guard on the existing tests). |

## Green

1. API: add the title sort and the stage filter with tests (happy, tie order, 422).
2. Web: single-query `useCatalogueState`; remove `CoveragePanel` from the catalogue page.
3. Add `CatalogueSummaryChips` and wire it to `useCatalogueListState`.
4. Add the Title column and the stage filter; strings in en and de.

## Refactor gate

Audit `useCatalogueState.ts` (a coverage branch may now be dead; delete it), `DiscoveryCataloguePage.tsx` (the `ReadyState` and `CatalogueReady` helpers shrink), `CatalogueIndexPanel.tsx`, and the API filter module (`catalogue_filter.py`: still one `conditions()` and one `ordering()`). Report what was removed or extracted, or "audited, nothing needed".

## Verification

```bash
cd apps/api && pytest tests/test_discovery_admin_list_query.py tests/test_discovery_admin_api.py && cd ../..
cd apps/web
npm run test -- src/features/discovery-admin
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

Manual (smoke in chapter 10): open both pages side by side; the top blocks differ and each answers one question (coverage: is the system healthy; catalogue: what rows do we have and where are they in the pipeline).

## Commits

`test(api): define the catalogue title sort and stage filter`, `feat(api): sort the catalogue by title and filter by stage`, `test(web): define the distinct catalogue summary`, `feat(web): give the catalogue its own summary, title column and stage filter`.

## Out of scope

Changing the coverage page or its cards, new coverage metrics, charts, a combined dashboard, filtering the summary counts by the active filters.
