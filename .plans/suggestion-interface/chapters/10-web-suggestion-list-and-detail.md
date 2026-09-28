---
name: "Chapter 10 — Web suggestion list and detail"
overview: "Public /suggestions and /suggestions/:id pages, mirroring the documents list and detail: status and kind filters, pagination, and a detail view showing the payload, source and submitter."
todos:
  - id: hooks
    content: "useSuggestionsListQuery, useSuggestionDetailQuery"
    status: completed
  - id: list
    content: "SuggestionsListPage, filters, cards"
    status: completed
  - id: detail
    content: "SuggestionDetailPage"
    status: completed
isProject: false
---

# Chapter 10 — Web suggestion list and detail

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/suggestions-web-read` · **Status:** implemented, PR open

**Depends on:** [7](07-list-and-detail-endpoints.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Anyone can browse the suggestion queue and open one, the same way `/documents` and `/documents/:id` work
today (D7). This chapter has no vote controls; those arrive in
[voting-moderation chapter 10](../../voting-moderation/chapters/10-web-vote-controls.md), which extends
these same pages.

## Design decisions

**Mirror the documents pages exactly**, so voting-moderation can slot vote controls in without a rewrite:

```
containers/SuggestionsListPage.tsx     ~ DocumentsListPage.tsx
containers/SuggestionDetailPage.tsx    ~ DocumentDetailPage.tsx
components/suggestions-list/SuggestionCard.tsx        ~ DocumentCard.tsx
components/suggestions-list/SuggestionFilters.tsx      ~ document-filters/
components/suggestions-list/SuggestionsListSkeleton.tsx
components/suggestion-detail/SuggestionDetailView.tsx  ~ DocumentDetailView.tsx
components/suggestion-detail/SuggestionPayloadSection.tsx  (kind-specific rendering)
components/suggestion-detail/SuggestionDetailSkeleton.tsx
```

**Payload rendering dispatches on kind**: a small `PAYLOAD_RENDERERS` map (`new_document` → title/URL/tags,
`new_requirement` → parent → required with a `→` and both linked to `/documents/:id`), so a third kind is
one more entry, matching the backend's kind-handler pattern (chapter 8).

**Filters** default to `status=pending`; a segmented control switches to "All", "Approved", "Rejected"
(`SuggestionFilters`, URL-synced like `useDocumentFilters`). Kind and jurisdiction filters are query-string
only for now (no picker UI), a documented seam.

**Card shows**: title (or parent → required for edges), status badge, source badge (person icon or crawler
icon), relative submission time. No submitter identity beyond what chapter 7 exposes.

**Empty and error states** reuse `DocumentsListQueryStatus`'s pattern via a small shared
`QueryStatusView` extracted in the refactor step if duplication would otherwise exceed the rule of three
(this is the second copy after documents'; extracting now is in scope, not a "later" seam).

## Files

**Add** — `apps/web/src/features/suggestions/{hooks/useSuggestionsListQuery.ts,
hooks/useSuggestionDetailQuery.ts, containers/SuggestionsListPage.tsx,
containers/SuggestionDetailPage.tsx, components/suggestions-list/*, components/suggestion-detail/*}`,
tests beside each.

**Edit** — `apps/web/src/app/routes.tsx`, `apps/web/src/i18n/fallback/{de,en}.json` and seeds
(`suggestions.*` status and kind labels), possibly
`apps/web/src/features/documents/components/*/DocumentsListQueryStatus.tsx` (extract shared view).

## Red tests

| Test | Asserts |
| --- | --- |
| `useSuggestionsListQuery · fetches with the status filter` | Query params |
| `SuggestionsListPage · defaults to pending and shows cards` | Initial render |
| `SuggestionsListPage · switching to Approved refetches with that status` | Filter change |
| `SuggestionsListPage · shows an empty state for no results` | Negative |
| `SuggestionsListPage · shows a query-error state` | Negative |
| `SuggestionCard · shows the crawler badge for a crawler source` | Icon/text |
| `SuggestionCard · shows the requirement arrow for an edge suggestion` | Payload kind |
| `SuggestionDetailPage · renders a new_document payload with a working official URL link` | Link `href` |
| `SuggestionDetailPage · renders a new_requirement payload with both documents linked` | Two links |
| `SuggestionDetailPage · unknown id shows the not-found view` | 404 mapping |
| `routes · /suggestions/:id needs no authentication` | Public |
| `i18n · every suggestions.* key exists in both fallback bundles` | Parity |

## Green

1. Hooks; test 1.
2. List page, filters, cards; tests 2–7.
3. Detail page and payload renderers; tests 8–10.
4. Routes and i18n; tests 11–12.

## Refactor gate

- `PAYLOAD_RENDERERS` keeps the detail view a lookup, not a branch chain.
- If the query-status extraction happens, both documents and suggestions import the shared component and
  their own tests stay green.
- Report the outcome.

## Progress

All 12 red tests plus supporting unit tests for the new components pass. `SuggestionRead` in the API
response carries the full row for both list and detail (chapter 7 never introduced a separate summary
schema), so the web `types/index.ts` reuses one `SuggestionRead` for both, tightening `kind`/`status`/
`source_type` from `string` to literal unions and adding `NewRequirementSuggestionPayload` alongside the
existing `SuggestionPayload` (kept as-is since `SuggestionForm`/`createSuggestion` still only produce
`new_document`).

Landed in the planned Green order, one commit per slice rather than one per test:

1. `useSuggestionsListQuery`, `useSuggestionDetailQuery`, `useSuggestionFilters`, and the `suggestionsApi`
   list/detail functions.
2. `SuggestionCard`, `SuggestionsListSkeleton`, and — per the refactor note below — the `QueryStatusView`
   extraction, landed together since the card needed the shared empty/error/populated shell to test against.
3. `SuggestionFilters` (a `StatusFilterChip` segmented control: Pending/All/Approved/Rejected, URL-synced)
   and `SuggestionsListPage`.
4. `SuggestionPayloadSection` with its `PAYLOAD_RENDERERS` map, `SuggestionDetailPage`, and the rest of the
   detail component tree.
5. `/suggestions` and `/suggestions/:id` routes (both outside `RequireAuth`) and the `suggestions.*` i18n
   keys, mirrored into `apps/api/scripts/seed_data/translations/{en,de}.json` to keep the fallback-parity
   test green.

**Refactor gate, resolved differently than drafted**: the chapter's refactor step proposed extracting
`QueryStatusView` conditionally, "if duplication would otherwise exceed the rule of three." Since this is
only the second copy of the loading/error/empty/populated shell (documents', then suggestions'), a strict
rule-of-three reading would defer the extraction — but the chapter's own design decision says to do it now
regardless ("extracting now is in scope, not a 'later' seam"), so `QueryStatusView<T>` was extracted to
`apps/web/src/components/feedback/QueryStatusView.tsx` in the same slice as `SuggestionCard`, and
`DocumentsListQueryStatus` was refactored to use it. `DocumentsListQueryStatus.test.tsx` was not touched and
stayed green throughout, confirming the extraction preserved behavior (the one snag: the populated-list item
wrapper had to become a `Fragment`, not a `Box`, so a card's linked root stays the direct child the existing
tests assert `aria-busy`/opacity against).

`PAYLOAD_RENDERERS` is a `Record<SuggestionKind, PayloadRenderer>` in `SuggestionPayloadSection.tsx`
dispatching to `NewDocumentPayloadView`/`NewRequirementPayloadView`; adding a third kind is one more map
entry. Since chapter 7's payload only carries `parent_document_id`/`required_document_id` UUIDs for
`new_requirement` (no denormalized titles), the edge card/detail link text is the document id itself, not a
title — the "documented seam" the design decisions call out, not an oversight.

One deviation from the file list: a `SuggestionsListHeader.tsx` and `SuggestionDetailHeader.tsx` were added
(not named in the chapter's file list, which only wildcards `components/suggestions-list/*` and
`components/suggestion-detail/*`) to keep parity with `DocumentsListHeader`/`DocumentHeader` per the "mirror
the documents pages exactly" decision, and to keep `SuggestionsListView`/`SuggestionDetailContent` under the
Sandi Metz size guidance.

`./ci.sh` is green except for `AppMenu.test.tsx`'s focus-assertion test, which fails identically on `main`
before this branch's changes (confirmed via a throwaway worktree) — a pre-existing environment flake
unrelated to this chapter, left untouched.

Commits on `feat/suggestions-web-read`:
1. `test(web): describe suggestion list and detail data hooks` /
   `feat(web): add suggestion list/detail queries, filters and API client`
2. `test(web): describe suggestion card, skeleton and shared query status view` /
   `feat(web): extract QueryStatusView and add suggestion list cards`
3. `test(web): describe suggestion filters and the suggestions list page` /
   `feat(web): add the public suggestions list page with status filters`
4. `test(web): describe suggestion payload rendering and the detail page` /
   `feat(web): add the public suggestion detail page with kind-dispatched payloads`
5. `test(web): describe public suggestion routes and suggestions.* i18n parity` /
   `feat(web): register /suggestions and /suggestions/:id as public routes`

PR opened against `main`.

## Verification

```bash
cd apps/web
npm run test -- src/features/suggestions src/features/documents
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: browse `/suggestions`, switch filters, open a `new_document` and a `new_requirement` suggestion.

## Out of scope

Vote controls and tallies (voting-moderation), moderation actions, search.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-web-read
```

```text
test(web): describe suggestion list filters and payload rendering

feat(web): add public suggestion list and detail pages
```
