---
name: "Chapter 8 — Collapse QueryStatus wrappers"
overview: "Replace five near-identical QueryStatus wrapper components and three copies of the plural-key logic with one shared component and hook."
todos:
  - id: count-hook
    content: "useCountLabel(namespace) extends useDocumentCountLabel"
    status: pending
  - id: shared-wrapper
    content: "One shared list-status component"
    status: pending
  - id: adopt
    content: "Five wrappers deleted or reduced to configuration"
    status: pending
isProject: false
---

# Chapter 8 — Collapse QueryStatus wrappers

**Repo:** `redtape` · **Branch:** `refactor/collapse-query-status-wrappers` · **Status:** planned

**Depends on:** chapter 7 · **Architecture:** [../00-architecture.md](../00-architecture.md) F2 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

Rule of three: the same wrapper appears five times. Each builds `renderItem`, `renderSkeleton`, `renderEmpty`, and `countLabel` around `QueryStatusView`. After this chapter there is one shared piece, and each feature supplies only its differences (item renderer, skeleton, empty copy, i18n namespace).

All paths are under `apps/web/src`.

## Files

- Wrappers: `features/documents/components/documents-list/DocumentsListQueryStatus.tsx`, `features/suggestions/components/suggestions-list/SuggestionsListQueryStatus.tsx`, `features/discovery-admin/components/DiscoveryTasksQueryStatus.tsx`, `features/documents/components/document-detail/DocumentDetailQueryStatus.tsx`, `features/suggestions/components/suggestion-detail/SuggestionDetailQueryStatus.tsx`.
- Plural key copy: `count === 1 ? "count_one" : "count_other"` at `DocumentsListQueryStatus.tsx:38`, `SuggestionsListQueryStatus.tsx:38`, `DiscoveryTasksQueryStatus.tsx:42`.
- Existing hook to extend, not duplicate: `features/taxonomy/hooks/useDocumentCountLabel.ts` — it already exists for documents and is not reused.
- Not-found check by the detail wrappers: they import `ApiRequestError` from `services/api` (`DocumentDetailQueryStatus.tsx:7`, `SuggestionDetailQueryStatus.tsx:7`); leave to chapter 9 unless trivial.
- Shared piece: `components/feedback/QueryStatusView.tsx` and the `QueryStatus` type from chapter 7.
- Existing tests: `DocumentsListQueryStatus.test.tsx`, `SuggestionsListQueryStatus.test.tsx`, `DocumentDetailQueryStatus.test.tsx`, and the container tests.

## TDD loop

### Red

1. `useCountLabel(ns)` happy path: returns the one-form label for 1 and the other-form for 0 and 5, per namespace (documents, suggestions, tasks).
2. `useCountLabel(ns)` negative path: an unknown namespace key falls back to the existing missing-key behaviour (pin it) and never throws.
3. Characterization: the existing list status tests (loading renders skeleton not cards, empty state, error offers retry with zero cards) run unchanged against the shared component.

### Green

1. Add `useCountLabel`, delete the three copies of the plural-key logic, and make `useDocumentCountLabel` a thin use of it (or remove it if it becomes a one-line wrapper that adds nothing).
2. Create a shared list-status component taking `status`, `items`, and one `config` object (renderItem, skeleton, empty, label namespace). Convert the three list wrappers to configuration; convert the two detail wrappers if they share the same shape, otherwise leave them and note why.
3. Delete dead code and keep the tests co-located.

### Refactor

Audit the shared component and each remaining wrapper: at most 3 props, about 5 lines per function, no boolean flags. Report the wrapper count before (5) and after, and lines removed.

## Verification

```bash
cd apps/web
npm run test -- src/components/feedback src/features/documents src/features/suggestions src/features/discovery-admin
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/collapse-query-status-wrappers
```

```text
test(web): cover useCountLabel for singular, plural, and unknown keys
refactor(web): share one list status component and the count label hook
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`.
