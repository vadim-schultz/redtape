---
name: "Chapter 3 — Documents list on candidates"
overview: "Re-source the /documents page onto the candidate list API, keep the existing chips, and add URL-backed search, sort and pagination, so every available document is reachable."
todos:
  - id: types-service
    content: "documentsApi.fetchDocuments calls /api/v1/candidates via toListParams; DocumentSummary gains tags and confidence"
    status: pending
  - id: url-state
    content: "q, sort_by, sort_order, offset in the URL beside domain/situation/group; any filter change resets offset"
    status: pending
  - id: search-sort-ui
    content: "Shared search box, sort select, Pagination on the documents page"
    status: pending
  - id: query-keys
    content: "queryKeys.documents.list carries the full list state"
    status: pending
  - id: i18n
    content: "New keys in web fallback en/de and the API seed en/de"
    status: pending
  - id: tests
    content: "Container, hook, service and component tests"
    status: pending
isProject: false
---

# Chapter 3 — Documents list on candidates

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/document-browse-confidence-documents-source` · **Status:** planned
**Depends on:** Chapter 2 ([02-browse-contract.md](02-browse-contract.md)) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

`https://redtape.cc/documents` lists every discovered document, can be searched by title and sorted, pages beyond the first 20, and still filters with the existing domain and life-situation chips. The visual confidence circle (chapter 4) and the two-stage chips (chapter 5) come next; this chapter changes the data and the controls only. Paths below are under `apps/web/src/`.

## Design

### Data layer — `features/documents/`

- `services/documentsApi.ts::fetchDocuments` calls `GET /api/v1/candidates` with `toListParams` from `services/listQuery/params.ts` (emits `q`, `sort_by`, `sort_order`, `offset`, `limit`, `filter[...]`). `filter[domain]` and `filter[situation]` are the CSV of the selected codes (D9). `fetchDocumentDetail` is untouched (dormant).
- `types/index.ts`: `DocumentSummary` becomes `{ id, title, description, tags: TaggedTerm[] (domains and situations, most confident first), confidence: number }`, mapped from `CandidateCard` in the service so components do not see candidate naming. `DocumentListResponse` drops `available_leaf_codes`.
- `hooks/useDocumentsListQuery.ts` takes the whole list state (filters and list query) and passes it to `fetchDocuments`; `placeholderData: keepPreviousData` stays. The `municipalityCode` argument goes away: the candidate list has no jurisdiction filter. Remove `LocationPicker` from the page (D8 records this; the picker's only job was `municipality_code` on the document list).
- `app/queryKeys.ts::queryKeys.documents.list(...)` takes the single list-state object, not positional arguments (the architecture test forbids inline `queryKey: [...]` literals, so all keys stay here).

### URL state

- `hooks/useDocumentFilters.ts` keeps `domain`, `situation` and (chapter 5) `group` as repeated params. Remove `leaf` (the facet never reached the API). Every toggle and `clear` also deletes `offset`.
- A second hook `hooks/useDocumentListState.ts` owns `q`, `sort_by`, `sort_order`, `offset` by reusing `useListQueryState` with a spec that declares no filters (`services/documentListQuery.ts`: sort keys `confidence | title | created_at`, default sort `confidence desc`, `defaultLimit: 20`, `maxLimit: 100`). `serializeListUrl` already preserves params it does not own, so both hooks coexist on one `URLSearchParams`.
- `utils/buildDocumentsHref.ts` (used by `DocumentTagsView`) is unchanged.

### UI — `components/DocumentsListView/`

- Search box: extract the submit-applied search form shared today by `features/candidates/components/CandidatesListView/CandidatesSearch.tsx` and `features/discovery-admin/components/ListSearch.tsx` into one component in `components/data-display/` (`ListSearchBox`), used by the documents page now and by the other two when they are touched. Do not leave a third copy. (If extracting the admin one risks scope, extract from `CandidatesSearch` — which chapter 7 deletes — and leave `ListSearch` as `observed` for the smell sweep.)
- Sort select: a native-styled Chakra `NativeSelect` with three labelled options and an asc/desc toggle button; writes through `useDocumentListState`.
- Pager: `components/data-display/Pagination.tsx` below the list, fed by `total`, `offset`, `limit` of the response.
- `DocumentCard.tsx` still links to its item page, now `/candidates/:id` (D10), shows title, description and plain tag badges (no circle yet).
- The page container passes the list state, filters and taxonomy down; stay within the 3-props rule by grouping into `list`, `filters`, `taxonomy` objects as the page already does.
- Remove `LeafFacet` and `availableLeafCodes` from `DocumentFilters` and `SituationFilterView`.

### i18n

Add `documents.search_label`, `documents.search_placeholder`, `documents.search_submit`, `documents.sort_label`, `documents.sort_confidence`, `documents.sort_title`, `documents.sort_newest`, `documents.sort_asc`, `documents.sort_desc` (exact names as the `documents.*` namespace allows) to **all four** files, which must stay deep-equal: `apps/web/src/i18n/fallback/en.json`, `de.json`, `apps/api/scripts/seed_data/translations/en.json`, `de.json` (`fallback.test.ts:55-57`).

## Tests

Happy path:
- `documentsApi.test.ts`: `fetchDocuments` sends `filter[domain]=a,b`, `filter[situation]=x,y`, `q`, `sort_by`, `sort_order`, `offset`, `limit`; maps a `CandidateCard` to `DocumentSummary` with tags and confidence.
- `DocumentsListPage.test.tsx`: typing a query and submitting writes `q` to the URL and refetches; changing the sort writes `sort_by`/`sort_order`; the pager moves `offset`; toggling a chip resets `offset`; a page of 20 of 57 shows the pager.
- `useDocumentListState.test.tsx`: defaults omit the URL params; values round-trip.

Negative path:
- An invalid `sort_by` in the URL falls back to the default (the spec ignores values it would refuse); a negative or non-numeric `offset` is ignored.
- Search of a blank string removes `q` instead of sending it.
- Empty result shows the empty state with a "clear filters" action that also clears `q`.

Keep `architecture.test.ts` green (components never import feature services; query keys only from `queryKeys`).

## Verification

```bash
cd apps/web && npx vitest run src/features/documents src/services/listQuery src/i18n
./ci.sh
```

## Refactor gate

Scan `DocumentsListPage.tsx`, `useDocumentFilters.ts`, `documentsApi.ts` and the extracted search box. Expect Duplicated Code (three search forms) and Long Parameter List (list/filters/taxonomy) — fix the first, group the second.

## Commits

- `feat(web): serve the documents list from the candidate API and map candidates to documents`
- `feat(web): URL-backed search, sort and pagination on the documents page`

## Out of scope

The confidence circle (chapter 4), group chips and colours (chapter 5), deleting the old candidates list (chapter 7), any API change.
