---
name: "Chapter 9 — Frontend layering"
overview: "Move network and error logic out of contexts and components into services and hooks; make presentational components presentational."
todos:
  - id: locale-service
    content: "fetchTranslations moves out of LocaleContext into a service"
    status: pending
  - id: auth-gateway
    content: "AuthContext receives its gateway instead of importing the default"
    status: pending
  - id: error-helpers
    content: "isNotFound and conflict helpers replace service error class imports in components and containers"
    status: pending
  - id: container-queries
    content: "DocumentFilters and EmitPreviewPanel stop owning queries"
    status: pending
isProject: false
---

# Chapter 9 — Frontend layering

**Repo:** `redtape` · **Branch:** `refactor/frontend-layering` · **Status:** planned

**Depends on:** chapter 8 · **Architecture:** [../00-architecture.md](../00-architecture.md) F3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

Layers have one job: services call the API, hooks hold logic and query state, containers compose, components present. Dependencies flow container → components and hooks → services → types and utils. No behaviour change.

All paths are under `apps/web/src`.

## Files

- `contexts/LocaleContext.tsx:25-37` — a raw `fetch` and `fetchTranslations` in a context file, plus `abortRef`, `isLoading`, `remote`, and `queryClient` interaction (109 lines, the largest source file). Move the fetch to `services/translationsApi.ts`, the state machine to a hook, and keep a thin provider.
- `features/auth/contexts/AuthContext.tsx` (95 lines) — imports `supabaseAuthGateway` directly (line 13) and does `queryClient` work (line 41). The provider takes the gateway as a prop with the real gateway chosen at the app root; tests already use `createFakeAuthGateway`.
- Components importing service error classes: `features/documents/components/document-detail/DocumentDetailQueryStatus.tsx:7` and `features/suggestions/components/suggestion-detail/SuggestionDetailQueryStatus.tsx:7` (`ApiRequestError`); `features/suggestions/containers/SuggestPage.tsx:10` (`SuggestionConflictError`). Add helpers (for example `isNotFound(error)` in `services/apiErrors.ts` or `utils/`) and a hook for the conflict handling.
- Presentational components owning queries: `features/documents/components/documents-list/document-filters/DocumentFilters.tsx:21-22` (`domains.refetch()`, `situations.refetch()`) and `features/discovery-admin/components/EmitPreviewPanel.tsx:19` (`previewQuery.refetch()`). Containers own the query and pass data and callbacks.
- Existing tests: `contexts/LocaleContext.test.tsx`, `features/auth/contexts/AuthContext.test.tsx`, `DocumentFilters.test.tsx`, `EmitPreviewPanel.test.tsx`, `SuggestPage.test.tsx`, `services/api.test.tsx`.

## TDD loop

One loop per item below; each has a happy and a negative test.

1. **Translations service.** Happy: `fetchTranslations(locale)` returns the parsed bundle. Negative: a non-OK response or network failure rejects with the domain error and the provider falls back to the bundled strings.
2. **Auth gateway injection.** Happy: the provider uses the injected fake gateway and exposes the signed-in state. Negative: sign-out clears cached queries (existing test) and a failing gateway yields the error state, not a crash.
3. **Error helpers.** Happy: `isNotFound` is true for a 404 `ApiRequestError`. Negative: false for 500, for a network error, and for non-error values.
4. **Presentational filters and preview.** Happy: the component renders data passed in and calls `onRetry` when asked. Negative: with an error flag it shows the retry control and never calls an API itself (no query hooks imported).

### Green and refactor

Implement one item at a time; rerun the narrow suite after each. Refactor gate per item: containing file at most about 100 lines, at most 3 props or parameters, one concern. Report the line count of `LocaleContext.tsx` and `AuthContext.tsx` before and after, and confirm with a grep that no component imports from `services/*` error classes.

## Verification

```bash
cd apps/web
npm run test -- src/contexts src/features/auth src/features/documents src/features/suggestions src/features/discovery-admin
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/frontend-layering
```

```text
test(web): cover translations service, error helpers, and presentational filters
refactor(web): move network and error handling out of contexts and components
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`. If one PR is too large, split by item.
