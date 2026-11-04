---
name: "Chapter 5 — Frontend category browsing and linked chips"
overview: "Replace dual-axis browse controls with search-first category navigation and compact red category chips that link to canonical filtered results."
depends_on:
  - 03-category-api-and-backend-filters
  - 04-ingest-and-llm-category-contract
touches:
  - apps/web/src/features/taxonomy/
  - apps/web/src/features/documents/
  - apps/web/src/features/candidates/
  - apps/web/src/components/
  - apps/web/src/app/queryKeys.ts
  - apps/web/src/i18n/fallback/
  - apps/web/src/test/
  - apps/api/scripts/seed_data/translations/
execution: chapter-implementer
todos:
  - id: taxonomy-client
    content: "Replace domain/group/situation queries with one category tree client, type model, and query key."
    status: pending
  - id: search-first
    content: "Make search primary and category browsing secondary with stable root/subcategory URL semantics."
    status: pending
  - id: category-chips
    content: "Render compact red linked category chips on document cards and detail headers without nested interactive markup."
    status: pending
  - id: tests
    content: "Update filter, URL, tag, card, detail, contract, translation, accessibility, and responsive tests."
    status: pending
---

# Chapter 5 — Frontend category browsing and linked chips

**Repo:** `redtape` (`apps/web`)
**Depends on:** [Chapter 3](03-category-api-and-backend-filters.md), [Chapter 4](04-ingest-and-llm-category-contract.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Make search the first interaction on the documents page and replace the dual-axis taxonomy controls with one compact category tree. Every document shows its canonical root/subcategory tags as red, compact links. Selecting a chip opens the same category-filtered document list as selecting the category on the front page.

The web matrix is already removed. This chapter must not restore a matrix route, matrix query, or intersection UI.

## Design decisions

- `useCategoryTreeQuery` is the only public taxonomy browse query. It returns canonical roots and children with localized names.
- Search controls render before category browsing. Category browsing may be collapsed or visually secondary but remains keyboard accessible and shareable.
- The URL uses repeated `category` codes, with the same encoding helper used by front-page filters and category chips.
- Selecting a root uses the backend descendant-inclusion rule. Selecting a subcategory links to that exact category code.
- Category chips use the existing red semantic token/theme used by front-page selections, not raw hex values. Their compact size is consistent across cards and detail headers.
- A chip is a real router link with a visible focus state and an accessible name. No chip is a button that manually mutates query state without a shareable URL.
- Document card composition must not nest category links inside a card anchor. If the card currently has a whole-card link, use a linked title/action region plus independent chips or extract a non-link card shell.
- Chips display only canonical product categories. PVOG source leaves, source labels, confidence internals, and old axis names do not appear in the category chip row.

## Files

| Path | Change |
| --- | --- |
| `apps/web/src/features/taxonomy/types/index.ts` | Add category node/tree and canonical tag types; remove axis-specific public types after compatibility. |
| `apps/web/src/features/taxonomy/services/taxonomyApi.ts` | Add the category tree client and remove/retire axis clients at the documented cutoff. |
| `apps/web/src/features/taxonomy/hooks/useCategoryTreeQuery.ts` | Add one locale-aware TanStack Query hook. |
| `apps/web/src/app/queryKeys.ts` | Add the central category query key and remove obsolete axis keys only after consumers migrate. |
| `apps/web/src/features/documents/hooks/useFilterTaxonomy.ts` | Consume the category tree and simplify retry/error handling. |
| `apps/web/src/features/documents/hooks/useDocumentFilters.ts` | Replace domain/group/situation selection state with category selection. |
| `apps/web/src/features/documents/utils/filterParams.ts` | Parse and serialize repeated category codes and compatibility aliases. |
| `apps/web/src/features/documents/utils/groupSelection.ts` | Remove or replace group expansion with category tree selection. |
| `apps/web/src/features/documents/utils/situationCodes.ts` | Retire after all callers use category descendants. |
| `apps/web/src/features/documents/utils/buildDocumentsHref.ts` | Build canonical category-filtered links for front-page controls and chips. |
| `apps/web/src/features/documents/components/DocumentsListView/DocumentListControls.tsx` | Put search first and category browsing second. |
| `apps/web/src/features/documents/components/DocumentsListView/DocumentFiltersView/` | Replace two-axis filter groups with root/subcategory category navigation. |
| `apps/web/src/features/documents/components/DocumentsListView/DocumentCard.tsx` | Make the card/chip interaction model valid without nested links. |
| `apps/web/src/features/documents/components/DocumentTagsView/` | Render canonical compact red linked category chips. |
| `apps/web/src/features/candidates/components/CandidateTagBadges/` | Render the same category chip contract on candidate/document detail surfaces. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateHeader.tsx` | Use canonical category tags and direct category links. |
| `apps/web/src/features/candidates/components/CandidateDetailView/` | Preserve detail layout while delegating accordion changes to chapter 8. |
| `apps/web/src/features/documents/types/index.ts` and `apps/web/src/features/candidates/types/` | Replace public domain/situation arrays with category tags and compatibility types. |
| `apps/web/src/i18n/fallback/{de,en}.json` | Add category/filter/chip/search copy and remove obsolete axis copy only at cutover. |
| `apps/api/scripts/seed_data/translations/{de,en}.json` | Keep translation parity with the web bundles. |
| `apps/web/src/test/contract/openapi.schemas.json` | Update generated category response/tag shapes. |

## Red tests

### Happy path

- `category tree hook · returns roots and children from one query` asserts the query key, locale, and service path.
- `category filter · selecting a root serializes one category code` asserts a shareable canonical URL.
- `category filter · selecting a subcategory serializes its exact code` asserts no domain/situation/group alias is added.
- `CategoryChip · uses the front-page red semantic token` asserts theme-token usage and compact size.
- `CategoryChip · links to the category-filtered list` asserts the top-level and subcategory hrefs.
- `DocumentCard/DetailHeader · renders canonical category chips` asserts labels come from the category tree.

### Negative path

- `category tree · failed query renders the existing query error and no stale chips` asserts safe failure.
- `category filter · unknown URL category does not produce a valid taxonomy selection` asserts validation/error behavior.
- `CategoryChip · is not nested inside another interactive element` asserts rendered markup and keyboard target count.
- `document card · chip click does not navigate to the document detail page` asserts the category link wins without event hacks.
- `legacy URL · old axis parameters follow the documented compatibility behavior` asserts old links do not silently show the wrong unfiltered result.

## Green

1. Add the category tree type, service, hook, query key, and fixtures.
2. Replace selection parsing/serialization and move search before taxonomy browsing.
3. Implement root/subcategory filter UI and compatibility URLs.
4. Extract or adapt a compact red `CategoryChip` used by card/detail surfaces.
5. Recompose cards so chips are independently clickable links.
6. Update translations, API contract fixtures, and tests.

## Refactor gate

Audit the complete web taxonomy and chip surface:

- components receive category data as props and never call services directly;
- the category query key is centralized;
- URL encoding lives in one pure helper;
- root expansion is not duplicated in the UI and backend;
- category chip visual and link behavior is shared rather than copied across card/detail components;
- no component uses a boolean prop to switch old-axis versus category rendering;
- no nested link or click-propagation workaround remains;
- components stay within the web size/prop conventions and use existing theme tokens.

Report the refactor outcome and rerun the narrow Vitest suite after each extraction.

## Verification

```bash
cd apps/web
npm test -- src/features/taxonomy src/features/documents src/features/candidates
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

Record URL, chip, i18n, and contract evidence in [../run-ledger.md](../run-ledger.md).

## Out of scope

Document-view accordion behavior, staged/completeness removal, admin-only tag editing, database migrations, embeddings, entity identification, and reintroducing the matrix.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b feat/category-frontend-browsing
```

```text
test(web): describe category browsing and linked chips
feat(web): make category browsing search-first
```
