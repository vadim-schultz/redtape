---
name: "Chapter 7 — QueryStatus object"
overview: "Pass query state as one QueryStatus object so QueryStatusView and the View/QueryStatus components take 3 props or fewer."
todos:
  - id: measure
    content: "Count props per component to get a baseline"
    status: pending
  - id: type-helper
    content: "QueryStatus type and toQueryStatus(query) helper"
    status: pending
  - id: adopt
    content: "QueryStatusView and the *View/*QueryStatus components take status as one prop"
    status: pending
isProject: false
---

# Chapter 7 — QueryStatus object

**Repo:** `redtape` · **Branch:** `refactor/query-status-object` · **Status:** planned

**Depends on:** chapter 6 (frontend starts after the backend chapters) · **Architecture:** [../00-architecture.md](../00-architecture.md) F1 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

Stop threading `isLoading`, `isRefreshing`, `isError`, `error`, and `onRetry` as five loose props. One `QueryStatus` object travels instead, and components stay at **3 props or fewer** (rule: more than 3 means an object). No visible behaviour change.

All paths are under `apps/web/src`.

## Files

- `components/feedback/QueryStatusView.tsx:6-17` — 11 props (the worst case).
- `features/documents/components/documents-list/DocumentsListView.tsx:10-32` (9 props), `DocumentsListQueryStatus.tsx`.
- `features/documents/components/document-detail/DocumentDetailView.tsx:8-23` (9), `DocumentDetailQueryStatus.tsx` (8).
- `features/suggestions/components/suggestions-list/SuggestionsListView.tsx:9-24` (8), `SuggestionsListQueryStatus.tsx`.
- `features/suggestions/components/suggestion-detail/SuggestionDetailView.tsx`, `SuggestionDetailQueryStatus.tsx`.
- `features/discovery-admin/components/DiscoveryTasksView.tsx:9-27` (7), `DiscoveryTasksQueryStatus.tsx`.
- Other 5-6 prop offenders: `DiscoveryAdminDisabled.tsx`, `EmptyStateCard.tsx`, `TitleFields.tsx`, `LocationBar.tsx` (5), `SelectSegment.tsx` (8).
- Containers that pass the loose booleans by hand: the Documents, Suggestions, and DiscoveryTasks pages (and the two detail pages), including `isRefreshing={q.isFetching && !q.isLoading}` and `onRetry={() => void q.refetch()}`.
- New: `components/feedback/queryStatus.ts` (type and `toQueryStatus`), with a test.

## TDD loop

### Red

1. `toQueryStatus` happy path: a loading query maps to `{isLoading: true, ...}`; a successful refetch maps to `isRefreshing: true`; `onRetry` calls `refetch`.
2. `toQueryStatus` negative path: an error query exposes the `error` and `isError`, and `onRetry` still refetches; success exposes no error.
3. Component level (existing tests are the safety net): `QueryStatusView` with `status.isError` offers retry and renders **zero** items; with `isLoading` renders the skeleton, not items.

Run first and confirm 1-2 fail (helper missing), 3 passes against the old API (characterization), then switch the props.

### Green

1. Add the `QueryStatus` type and `toQueryStatus(query)`.
2. Change `QueryStatusView` to take `status` plus the render props grouped as one `slots` object (or reduce through chapter 8). Target at most 3 props.
3. Update each View, QueryStatus component, and container to pass `status`. Update the existing component tests to the new props (no behaviour change in assertions).
4. Reduce other 5-8 prop components (`SelectSegment`, `LocationBar`, `TitleFields`, `EmptyStateCard`, `DiscoveryAdminDisabled`) by grouping related props into one object or by composition.

### Refactor

Audit each touched component per the checklist: at most 3 props, small, one concern, no boolean props that switch behaviour. Re-run the narrow suite after each file. Report prop counts before and after for each component.

## Verification

```bash
cd apps/web
npm run test -- src/components/feedback src/features
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/query-status-object
```

```text
test(web): cover toQueryStatus for loading, refreshing, and error queries
refactor(web): pass query state as one QueryStatus object
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`.
