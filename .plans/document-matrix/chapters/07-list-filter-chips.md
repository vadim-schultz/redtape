---
name: "Chapter 7 — List filter chips"
overview: "Domain and life-situation filter chips on the documents list, state held in URL search params and passed to the documents API."
todos:
  - id: api
    content: "fetchDocuments accepts domain and situation code lists"
    status: pending
  - id: state
    content: "useDocumentFilters hook reads and writes search params"
    status: pending
  - id: ui
    content: "DocumentFilters component with chip groups and clear action"
    status: pending
isProject: false
---

# Chapter 7 — List filter chips

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/matrix-list-filters` · **Status:** planned

**Depends on:** [4](04-documents-filter.md), [6](06-web-taxonomy-client.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`/documents?domain=wohnen&situation=umzug` shows only matching documents; users toggle chips to change
the filter; the URL is the source of truth, so links from the matrix (chapter 8) and browser back/forward
just work. With no params the page behaves exactly as today.

## Design decisions

**URL as state.** `useSearchParams` from react-router; a `useDocumentFilters()` hook returns
`{domains, situations, toggleDomain, toggleSituation, clear}`. No parallel `useState`, so no drift
between chips and query. Alternative: local state synced to the URL — rejected as two sources of truth.

**Query key includes filters** in
[useDocumentsListQuery.ts](../../../apps/web/src/features/documents/hooks/useDocumentsListQuery.ts):
`["documents", municipalityCode, domains, situations, locale]`; `placeholderData: keepPreviousData` stays
so chip toggles do not flash a skeleton.

**Component split (one per file, directory mirrors hierarchy):**
`components/documents-list/document-filters/{DocumentFilters, FilterGroup, FilterChip}.tsx`.
`DocumentsListPage` composes them above the list; the existing location bar stays untouched.

**Arrival from the matrix.** A row header links to `?situation=S`, a column header to `?domain=D`, a cell
to both; the list page needs no special case, the corresponding chip(s) simply render as pressed. Tested
end to end with a memory router starting at each URL shape.

**Chips use Chakra namespace APIs** and theme tokens (selected = `primary`, unselected = subtle
surface); each chip is a real toggle button with `aria-pressed`. A group heading uses the existing
section text style.

**Failure isolation.** If the taxonomy query fails, the list still works and the filter area shows the
shared [QueryError](../../../apps/web/src/components/feedback/QueryError.tsx) compactly; it never blocks
the list.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/web/src/features/documents/hooks/useDocumentFilters.ts` | URL-backed filter state |
| `apps/web/src/features/documents/components/documents-list/document-filters/*.tsx` | `DocumentFilters`, `FilterGroup`, `FilterChip` + tests |

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/features/documents/services/documentsApi.ts` | `domain` / `situation` repeatable query params |
| `apps/web/src/features/documents/hooks/useDocumentsListQuery.ts` | Accept filters; extend key |
| `apps/web/src/features/documents/containers/DocumentsListPage.tsx` | Compose filters, pass to hook |
| `apps/web/src/features/documents/components/documents-list/DocumentsListView.tsx` | Slot for filters |

## Red tests

| Test | Asserts |
| --- | --- |
| `useDocumentFilters · reads domains and situations from the URL` | Parsed arrays |
| `useDocumentFilters · toggle adds then removes a code` | URL round trip |
| `useDocumentFilters · ignores empty and duplicate values` | Negative |
| `documentsApi · sends repeated domain params` | `domain=a&domain=b` |
| `documentsApi · sends no filter params when none selected` | Regression guard |
| `FilterChip · reports pressed state via aria-pressed` | Accessibility |
| `DocumentFilters · clear removes all filters` | URL empty |
| `DocumentsListPage · /documents?situation=X shows only the situation chip pressed` | Row selection arrival |
| `DocumentsListPage · /documents?domain=D shows only the domain chip pressed` | Column selection arrival |
| `DocumentFilters · unknown code in the URL is ignored with no crash` | Negative; API 422 surfaces via `QueryError` |
| `DocumentFilters · taxonomy error shows compact error and keeps list usable` | Negative |
| `DocumentsListPage · empty filtered result renders the empty state` | Not an error |

## Green

1. API params; hook; tests.
2. `FilterChip` → `FilterGroup` → `DocumentFilters`, each with its own test.
3. Wire into page; page-level test with a memory router.

## Refactor gate

- `DocumentsListPage` is ~25 LOC now; adding filter wiring must not push it past ~30. Move
  query-argument assembly into `useDocumentFilters`.
- `useDocumentFilters` toggling is one function parameterized by axis, not two copies.
- Nesting: no conditional-in-map inside JSX; extract rows into components.

## Verification

```bash
cd apps/web
npm run test -- src/features/documents
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: open `/documents?situation=umzug`, toggle a domain chip, use back/forward.

## Out of scope

Matrix page (chapter 8), tag badges (chapter 9), pagination changes, saving filters per user.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-list-filters
```

```text
test(web): describe URL-backed document filters

feat(web): filter the documents list by domain and life situation
```
