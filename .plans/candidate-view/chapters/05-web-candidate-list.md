---
name: "Chapter 5 — Web candidate list"
overview: "Add the public /candidates page: a ranked list of candidate cards with completeness chips, search, domain and situation chips, a complete-only switch, Chakra pagination and explicit states, backed by a new features/candidates slice, a query-keys group, i18n strings and a menu icon link."
todos:
  - id: slice
    content: "Create features/candidates types, candidatesApi service, list spec, hooks and the queryKeys group."
    status: pending
  - id: cards
    content: "Build CompletenessChips and the list variant of CandidateCard on AppCard."
    status: pending
  - id: page
    content: "Build the list page with banner, search, taxonomy chips, complete-only switch, pagination and states; register /candidates and the menu link."
    status: pending
  - id: i18n-tests
    content: "Add candidates.* strings in en and de and the paired tests."
    status: pending
isProject: false
---

# Chapter 5 — Web candidate list

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/candidate-view-web-list` · **Status:** planned  
**Depends on:** [03-public-candidate-api.md](03-public-candidate-api.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (sections 4, 5, 6) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

A visitor opens `/candidates` without logging in and sees every staged candidate as a card in the
front-page style, best-complete first (decision D1). Each card shows the title, the description line,
accepted domain and situation tags, and five completeness chips. The visitor can search titles, narrow by
one domain and one situation, switch to "complete only", and page through the result. A banner says the
candidates are staged and unreviewed (D16). The app menu gains a Candidates icon link. The item page
`/candidates/:id` is chapter 6; this chapter registers only `/candidates`, and the cards link to the path
that chapter 6 will serve.

## Design decisions

- **Types mirror the API exactly** (chapter 3, architecture section 4). `CandidateCard`: `id`, `key`,
  `title`, `description`, `description_source`, `domains[]`, `situations[]` (each `{code, name}`),
  `status`, `completeness` (0 to 5), `complete`, `flags` (`{has_domain, has_situation, has_edges,
  has_snapshot, has_screenshot}`, nested exactly as chapters 3 and 4 return them), `mention_count`. List envelope `{items, total, offset, limit}`. No field is renamed or
  derived on the client.
- **List state uses the shared contract.** A `CANDIDATE_LIST_SPEC` (`ListQuerySpec` of
  `src/services/listQuery`) declares sort keys `completeness | title | mentions | created_at`, filters
  `complete` (`oneOfFilter` of `yes | no`), `domain` and `situation` (a non-empty taxonomy code string), and
  limit 20 (max 100). `useListQueryState` keeps it in the URL (`q`, `sort_by`, `filter[...]`, `offset`), and
  `toListParams` produces the request. The default (no sort in the URL) sends no `sort_by`; the API default is
  completeness descending. Search, filter or sort changes reset the offset (existing transitions).
- **Chips are single-select per axis.** The API takes one `filter[domain]` and one `filter[situation]`; a
  chip click sets that filter, a second click on the active chip clears it. This differs from the front
  page, which ORs several codes; do not reuse `useDocumentFilters`.
- **Taxonomy names come from the taxonomy feature's hooks** (the ones `useFilterTaxonomy` in
  `features/documents` wraps), not from a copy. If `src/architecture.test.ts` forbids that cross-feature
  import, move the shared chip row into `src/components/` as a presentational component taking
  `{terms, active, onSelect}` and let both features compose it; do not duplicate the fetch.
- **Cards reuse `AppCard`** and the `DocumentCard` typography (`subsectionHeader` title, `Card.Description`).
  The card links to `/candidates/${id}`. It shows at most the first two lines of the description
  (`lineClamp`), the tags as small badges, and `CompletenessChips` along the bottom.
- **`CompletenessChips`** renders the five flags as a row of labelled chips (`has_domain`, `has_situation`,
  `has_edges`, `has_snapshot`, `has_screenshot`); a true flag is filled with a check icon, a false flag is
  an outline with a dash. Text labels are always visible and each chip has an accessible name such as
  "Screenshot: missing". The component takes `{flags}` (a typed `CompletenessFlags` object) so chapters 6
  and 8 reuse it.
- **Complete-only switch** sets `filter[complete]=yes`; off removes it. No `no` option in the UI.
- **No image in the list** (D3, architecture section 11): the card shows the `has_screenshot` flag only.
- **Banner** is a plain `Alert` with `candidates.banner_title` and `candidates.banner_body`; it is shown
  above the list in every state, including error and empty.
- **States** use `ListQueryStatus` with `toQueryStatus`: skeleton while loading, an explicit empty state
  (`candidates.empty_title` and `empty_description`; when a filter is active it says the filters hide
  everything and offers a clear action), a retryable error, and a refreshing hint via `keepPreviousData`.
  Pagination is the shared Chakra `Pagination`, hidden for a single page.
- **Route** `/candidates` is added to `src/app/routes.tsx` with `lazy` import and its own
  `CandidatesListSkeleton` fallback, no guard. The menu link is a third `MenuIconLink` in
  `DocumentsMenuRow` (icon from `react-icons`, for example `LuLayers`; `aria-label` and `title` from
  `nav.candidates`) placed before `<DiscoveryAdminMenuLinks />`.
- **i18n.** Keys under `candidates.*` (`title`, `subtitle`, `banner_title`, `banner_body`, `search_label`,
  `filter_domain`, `filter_situation`, `complete_only`, `clear_filters`, `count_one`, `count_other`,
  `empty_title`, `empty_description`, `flag_domain`, `flag_situation`, `flag_edges`, `flag_snapshot`,
  `flag_screenshot`, `flag_present`, `flag_missing`, `from_source`) and `nav.candidates`, added to **both**
  `src/i18n/fallback/en.json` and `de.json`. The German strings are written in German, not copied.

## Files

**Create**

- `apps/web/src/features/candidates/types/index.ts` (`CandidateCard`, `CandidateListResponse`,
  `CompletenessFlags`, `TaxonomyTag`)
- `apps/web/src/features/candidates/services/candidatesApi.ts` (`fetchCandidates(query)`)
- `apps/web/src/features/candidates/services/candidateListQuery.ts` (`CANDIDATE_LIST_SPEC`)
- `apps/web/src/features/candidates/hooks/useCandidateListState.ts`, `useCandidatesQuery.ts`
- `apps/web/src/features/candidates/components/CompletenessChips/` (`CompletenessChips.tsx`, `index.ts`)
- `apps/web/src/features/candidates/components/CandidatesListView/` (`CandidatesListView.tsx`,
  `CandidatesBanner.tsx`, `CandidatesFilters.tsx`, `CandidateListCard.tsx`, `CandidatesListQueryStatus.tsx`,
  `CandidatesListSkeleton.tsx`, `index.ts`)
- `apps/web/src/features/candidates/containers/CandidatesListPage.tsx`
- a test file beside each of the above

**Edit**

- `apps/web/src/app/queryKeys.ts` (a `candidates` group: `list(query, locale)`; chapter 6 adds `detail`)
- `apps/web/src/app/routes.tsx` (the `/candidates` route)
- `apps/web/src/components/layout/menu/DocumentsMenuRow.tsx` (the link)
- `apps/web/src/i18n/fallback/en.json`, `de.json`
- `apps/web/src/app/routes.*.test.tsx` or `App.test.tsx` for the route assertion, following the existing
  pattern

**Do not edit**

- `features/documents` components or `useDocumentFilters`
- the DataTable kernel and `features/discovery-admin`
- backend files; the API contract of chapter 3 is the input
- `/candidates/:id` (chapter 6)

## Red tests

| Test | Asserts |
| --- | --- |
| `candidate list spec serializes the canonical query` | Happy: state with `q`, `filter[domain]`, `filter[complete]=yes` and a sort maps to `q`, `filter[domain]`, `filter[complete]`, `sort_by`, `sort_order`, `offset`, `limit` on the request and round-trips through the URL. |
| `candidate list spec rejects an invalid complete value` | Negative: `filter[complete]=maybe` in the URL parses to the default (no filter); no invalid value reaches the request. |
| `candidate list state resets the offset on a filter change` | Negative: from offset 40, selecting a domain chip yields offset 0; a page change alone keeps the filter. |
| `candidates list renders cards with title, tags and chips` | Happy: a stubbed page of three candidates shows three links to `/candidates/<id>`, the title, the description, tag badges and five chips each with a visible label. |
| `completeness chips announce present and missing flags` | Happy and negative: a candidate with `has_screenshot=false` has a chip whose accessible name says "Screenshot: missing"; a complete candidate has five "present" chips. |
| `candidates list shows the unreviewed banner in every state` | Happy: banner text present while loading, populated, empty and error. |
| `candidates list shows an empty state that explains active filters` | Negative: an empty page with `filter[complete]=yes` shows the empty title plus a clear-filters action; clicking it removes the filter and refetches. |
| `candidates list shows a retryable error` | Negative: a 503 stub shows the error with a retry; retry refetches and renders the list. |
| `domain chip toggles a single filter` | Happy: clicking an inactive chip sets the filter; clicking the active chip clears it; the other axis is untouched. |
| `complete-only switch sets and clears the filter` | Happy: on sets `filter[complete]=yes`, off removes it. |
| `pagination appears only for more than one page` | Negative: total 15 at limit 20 renders no pagination; total 45 renders it and a page change keeps the filters. |
| `app routes /candidates without a guard` | Happy: an anonymous visitor at `/candidates` sees the list, not the login page; negative: `/candidates/<id>` still falls through to not-found until chapter 6. |
| `menu shows the candidates link` | Happy: the Documents row contains a link named by `nav.candidates` to `/candidates`; negative: it is present for an anonymous visitor and does not depend on the admin probe. |
| `candidates strings exist in en and de` | Happy: every key listed above resolves in both bundled bundles; negative: a missing key in either fails the existing key-parity test. |

Write and run the red tests before implementation, with `renderWithProviders` and the existing `fetch`
stubbing pattern (`src/test/setup.ts` stubs `fetch` with a 503 by default, so each test stubs what it needs).

## Green

1. Add types, the list spec, the service and the query-keys group; make the spec and state tests pass.
2. Add `useCandidateListState` (a thin wrapper over `useListQueryState` with the spec) and
   `useCandidatesQuery` (`useApiQuery`, `placeholderData: keepPreviousData`, locale in the key).
3. Build `CompletenessChips`, then `CandidateListCard`; make the card tests pass.
4. Build the banner, the filters row (search form, two chip rows, the switch, the clear action), the status
   wrapper and the skeleton; compose them in `CandidatesListView`; add the container.
5. Register the route and the menu link; add the strings to both bundles.
6. Run the narrow suite after each step.

## Refactor gate

Audit the whole `features/candidates` slice and the `DocumentsMenuRow`. Each component stays at about three
props and one hundred lines, each function at about five lines, with one nesting level; extract the filter
row parts (search, chip row, switch) into named components rather than growing `CandidatesFilters`. Check
the import direction (container, then components and hooks, then services, then types and utils), that no
component imports a `services/*` file, that the only query keys come from `src/app/queryKeys.ts`, and that
`src/architecture.test.ts` still passes. Count every arm for the rule of three: the chip row is used for
domains and situations, so it is one component taking `{terms, active, onSelect}`. Report the outcome and rerun
the narrow suite.

## Verification

```bash
cd apps/web
npm run test -- src/features/candidates src/app src/components/layout --run
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

Manual look (optional while no browser agent is available): `npm run dev` with the API running, open
`/candidates`.

## Out of scope

- The item page, the diagram and the screenshot (chapters 6 and 7)
- Sorting controls beyond the default ranking and a title/mentions sort menu if the implementer finds none
  needed; the list contract supports them, the UI does not have to expose them
- Thumbnails, saved filters, multi-select chips
- Admin tables (chapters 8 and 9)

## Git workflow

```bash
git checkout feat/plans-candidate-view && git pull
git checkout -b feat/candidate-view-web-list
```

Suggested commits:

```text
test(web): define the candidate list state and cards
feat(web): add the public candidate list page
feat(web): link the candidate list from the app menu
```

Open the chapter PR into `feat/plans-candidate-view`.
