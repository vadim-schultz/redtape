---
name: "W1 — Admin query plumbing"
overview: "One useAdminQuery injects locale and token so the 12 accessToken! assertions disappear; services take one AdminAuth; defineListSpec and inlined one-line list-state wrappers; useApi leaves the shared HTTP client."
todos:
  - id: characterize
    content: "Pin URL, bearer header and signed-out behaviour of every admin query hook"
    status: pending
  - id: use-admin-query
    content: "useAdminQuery (skipToken, no non-null assertions); services take AdminAuth; 12 hooks adopt it"
    status: pending
  - id: list-spec
    content: "defineListSpec for the three admin specs and the documents spec; inline the three use*ListState wrappers and useCatalogueState"
    status: pending
  - id: move-use-api
    content: "Move useApi out of services/api.ts into hooks/useApi.ts"
    status: pending
isProject: false
---

# W1 — Admin query plumbing

**Repo:** `redtape` · **Branch:** `refactor/admin-query-plumbing` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-audit-report.md](../00-audit-report.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `web/features/discovery-admin/{hooks,services}`, `web/services/api.ts`, `web/hooks/` (plus the footprint listed under Files that the rollout table does not name: the three list-state import lines in containers and components, `types/listControllers.ts`, `services/listQuery/spec.ts`).
**After:** none. W3 and W4 start after this chapter.

**Findings:** D10, D11, L8, hygiene "web one-line wrappers".

## Goal

Behaviour-preserving. Every discovery-admin query hook stops repeating `useLocale` + `useAuth` + `accessToken!`. After the chapter:

- `accessToken!`, `candidateId!`, `catalogueId!` and `session!` assertions are gone from `features/discovery-admin/hooks/` (measured today: 12 lines with `accessToken!`, 7 with `candidateId!`/`catalogueId!`, plus `session!.accessToken` in `useDiscoveryAdminProbe.ts:20`; the same grep over `src` finds no other hits outside tests).
- The 11 `{locale, accessToken}` parameter objects in `discoveryAdminApi.ts` become one `AdminAuth` first argument.
- The shared `services/api.ts` no longer imports from `features/auth` or `contexts`; `useApi` lives in `hooks/`.
- The four list specs share defaults and type inference through `defineListSpec`; the three `use*ListState` pass-throughs and `useCatalogueState` are gone.

Not in scope: `useMe` (`accessToken as string` in `features/auth/hooks/useMe.ts:15`, owned by the auth feature, W2 touches `features/auth`), response validation (W3), panel container queries (W4).

## Design decisions

| Question | Decision | Why |
| --- | --- | --- |
| Where does the token go? | `apiRequest` keeps its optional `accessToken`; the admin service functions take `auth: AdminAuth` (`{ locale: string; accessToken: string }`) and spread it: `apiRequest<T>(path, { ...auth, query })`. | Reading the session inside `apiRequest` would put React context back into the shared client (L8). A bound client class would be a new abstraction for 11 call sites, and `useApi` already is the bound form. |
| Where does the token become non-optional? | `useAdminQuery` (new, `features/discovery-admin/hooks/useAdminQuery.ts`) builds the `AdminAuth` only when a token exists; otherwise it passes TanStack's `skipToken` as `queryFn`. | `skipToken` removes both the `enabled: Boolean(accessToken)` flag and the `!` in one place, with no cast. |
| Optional ids (`candidateId: string \| undefined`) | The hook passes `call` only when the id is truthy: `id ? (auth) => fetchX(auth, id) : undefined`. `useAdminQuery` treats `undefined` like a missing token. | `id` is narrowed inside the arrow (parameter never reassigned), so no `!`. Same truthiness rule as today's `Boolean(candidateId)`. |
| Query keys | Stay in `app/queryKeys.ts` (`apps/web/CLAUDE.md`). `useAdminQuery` takes a key factory `(locale) => QueryKey`, so `queryKeys.discoveryAdmin.coverage` is passed as is and `architecture.test.ts` (no inline `queryKey: [`) still holds. | Keys keep including the locale; no key shape changes, so cache behaviour is identical. |
| `defineListSpec` | New `services/listQuery/spec.ts`: takes `{ sortKeys, filters, defaultLimit = 20, maxLimit = 100 }`, returns `ListQuerySpec<SortKey, FilterKey>`, infers both key unions from its arguments. Exported through the existing `services/listQuery/index.ts`. | Four specs repeat `defaultLimit: 20, maxLimit: 100` today (`taskListQuery.ts`, `candidateListQuery.ts`, `catalogueListQuery.ts`, `documents/services/documentListQuery.ts`). The inference is what lets W3 derive the unions from the arrays (T2). It is not a one-line wrapper: it owns the defaults and the inference. |
| Where do the `CandidateList`, `TaskList`, `CatalogueList` aliases go? | New `features/discovery-admin/types/listControllers.ts`, each `ListQueryController<…SortKey, …FilterKey>`. | Components may not import a feature `services/*` (architecture test); they import types from `../types` or `../hooks` today. `ListQueryController` stays in `hooks/useListQueryState.ts` (moving it is a W3 option because W3 owns `services/listQuery`). |

## Files

All paths under `apps/web/src`.

| File | Change |
| --- | --- |
| `features/discovery-admin/hooks/useAdminQuery.ts` (+ `.test.tsx`) | New. Reads `useLocale()` and `useAuth()`, returns `useApiQuery(keyFor(locale), run, options)`. |
| `hooks/useApiQuery.ts` (20 lines) | `queryFn` parameter widened to `(() => Promise<T>) \| SkipToken`. `hooks/useApiQuery.test.tsx` gains a skipToken case. |
| `features/discovery-admin/services/discoveryAdminApi.ts` (195 lines) | Export `type AdminAuth`; the 13 functions take `(auth: AdminAuth, …)` instead of one object with `locale` and `accessToken`: `probeDiscoveryAdminAccess`, `listDiscoveryTasks`, `listDiscoveryCatalogue`, `fetchDiscoveryCoverage`, `fetchCataloguePipeline`, `fetchEmitPreview`, `listDiscoveryCandidates`, `fetchDiscoveryCandidate`, `fetchCandidateEdges`, `fetchCandidateEmitPreview`, `listCatalogueArtifacts`, `listCandidateArtifacts`, `fetchDiscoveryBudgets`. (Re-count at start: 13 exported functions, 12 hooks plus the probe.) |
| `features/discovery-admin/hooks/use{CandidateEdges,DiscoveryArtifacts,DiscoveryBudgets,DiscoveryCandidateArtifacts,DiscoveryCandidateEmitPreview,DiscoveryCandidate,DiscoveryCandidates,DiscoveryCatalogue,DiscoveryCoverage,DiscoveryEmitPreview,DiscoveryPipeline,DiscoveryTasks}Query.ts` | Adopt `useAdminQuery`. Each shrinks to key factory, service call and its own options (`keepPreviousData`, `ARTIFACT_STALE_MS`). `ARTIFACT_STALE_MS` stays exported from `useDiscoveryArtifactsQuery.ts` (a test and `useDiscoveryCandidateArtifactsQuery.ts` import it). |
| `features/discovery-admin/hooks/useDiscoveryAdminProbe.ts` | Uses `useAdminQuery` with `{ enabled: status === "authenticated", retry, retryDelay }`; drops `session!`. |
| `services/listQuery/spec.ts` (+ test), `services/listQuery/index.ts` | New `defineListSpec`; one export line. |
| `features/discovery-admin/services/{task,candidate,catalogue}ListQuery.ts`, `features/documents/services/documentListQuery.ts` | Use `defineListSpec`. Existing `*.test.ts` files stay green unchanged. |
| `features/discovery-admin/hooks/use{Task,Candidate,Catalogue}ListState.ts`, `useCatalogueState.ts` (+ `useCatalogueState.test.tsx`) | Deleted. |
| `features/discovery-admin/types/listControllers.ts` | New: `TaskList`, `CandidateList`, `CatalogueList`. |
| `features/discovery-admin/containers/Discovery{Tasks,Documents,Catalogue}Page.tsx` | Call `useListQueryState(TASK_LIST_SPEC)` etc. The catalogue page then mirrors the other two (query + `toQueryStatus`). |
| `features/discovery-admin/components/{DiscoveryTasksTable,DiscoveryTasksView,DiscoveryDocumentFilters,DiscoveryDocumentsTable,CatalogueSummaryChips,CatalogueServicesTable,CatalogueIndexPanel}.tsx` | Import lines only (`../hooks/use…ListState` becomes `../types/listControllers`). `CatalogueIndexPanel` takes `page`, `status`, `list` instead of `panel` and `list`. Nothing else changes in these files (W4 restructures them later). |
| `services/api.ts` (108 lines) | Remove `useApi`, `useMemo`, `useAuth`, `useLocale` imports. Result: HTTP client plus `ApiRequestError` only. |
| `hooks/useApi.ts` (+ `useApi.test.tsx`) | New home of `useApi`; the test moves out of `services/api.test.tsx`. |
| `hooks/useLocalesQuery.ts` | Import path of `useApi` changes. |

Facts checked against the source: `useApi` has one consumer (`hooks/useLocalesQuery.ts`) and one test (`services/api.test.tsx`); `CandidateList`, `TaskList` and `CatalogueList` are imported by exactly seven components (listed above) and nothing else; `@tanstack/react-query` is 5.103.2 installed, so `skipToken` is available.

## TDD loop

### Red

Characterisation first (these pass against the current code and must still pass after each step). New file `features/discovery-admin/hooks/discoveryAdminQueries.test.tsx`, table-driven over all 12 hooks with `renderWithProviders` and a `createFakeAuthGateway({ session })` (pattern from `useDiscoveryArtifactsQuery.test.tsx`):

1. `discovery admin queries · %s requests its path with the bearer token and locale` (`it.each` over hook, expected path, expected query string): asserts pathname, `Authorization: Bearer t`, `Accept-Language: en`, and for the list hooks the canonical `limit/offset/sort_by` params from `toListParams`. Happy path.
2. `discovery admin queries · %s sends nothing while signed out` (gateway with `configured: false`, no session): zero admin fetches, status stays `pending`. Negative path.
3. `discovery admin queries · %s sends nothing for a missing id` (the seven id hooks called with `undefined`): zero fetches. Negative path.

New behaviour, failing because the code does not exist yet:

4. `useAdminQuery · passes the locale and token to the call` and `· re-keys when the locale changes` (happy).
5. `useAdminQuery · does not call while there is no session`, `· does not call when the call is undefined`, `· honours enabled: false from options` (negative; the call spy is never invoked).
6. `useApiQuery · a skipToken query function never runs` (negative).
7. `defineListSpec · applies 20 and 100 as default and max limit`, `· keeps explicit limits`, `· keeps sortKeys and filters as given` (happy). The existing `*ListQuery.test.ts` files cover rejection of unknown filter values and must stay green unchanged.
8. `useApi · attaches the current session token` moved to `hooks/useApi.test.tsx` (fails: module missing); `useApi · sends no Authorization header when signed out` (negative, new).
9. `apiRequest` stays tested in `services/api.test.tsx` with its two existing cases; add `apiRequest · throws ApiRequestError with status and body for a non-OK response` if no test in `services/api.test.tsx` or `apiErrors.test.ts` covers it (the file has only the two bearer-header cases and the `useApi` case today).

Run `npm test -- src/features/discovery-admin/hooks src/hooks src/services` and confirm 4-8 fail, 1-3 pass.

### Green

1. Widen `useApiQuery` for `skipToken`. Add `useAdminQuery` and `AdminAuth`. Convert `discoveryAdminApi.ts` and the 12 hooks plus the probe in one commit (type errors guide the sweep). Rerun 1-3 unchanged.
2. Add `defineListSpec`; convert the four specs. Add `types/listControllers.ts`; replace the container calls; update the seven component imports; delete the three `use*ListState` files, `useCatalogueState.ts` and its test. The four behaviours that `useCatalogueState.test.tsx` pinned (rows carried, pending, error flag, no coverage call) are already pinned by `DiscoveryCataloguePage.test.tsx` ("does not request coverage", "a failed catalogue query shows retry and no chips", "a failed refetch keeps the previous rows and the chips"); verify before deleting, and port any that is not.
3. Move `useApi` to `hooks/useApi.ts`, split its test, repoint `useLocalesQuery`. Drop now-unused imports from `services/api.ts`.

### Refactor

Judge by responsibility. Look at: the seven id hooks repeating `id ? (auth) => fetchX(auth, id) : undefined` (apply the rule of three: three sites already, so extract a named `forId` helper only if the repetition reads as noise after conversion; otherwise leave it, since a helper must not become a one-line wrapper); `discoveryAdminApi.ts` repeating the path prefix (`/api/v1/discovery/admin`) in two literals (`fetchCataloguePipeline`, `fetchEmitPreview`) while the constants exist for the rest (use `CATALOGUE_PATH`); `ARTIFACT_PAGE_SIZE` query duplicated in two functions (one small constant object if it reads better). No `any`, no `as`, no `!` in the touched files; `grep` confirms. Report `Refactor gate: smells found -> …, refactorings applied -> …` with before and after numbers: lines of `discoveryAdminApi.ts` (195), total non-test lines in `features/discovery-admin/hooks` (402 today), count of `!` assertions (19 plus 1) and of `useLocale`/`useAuth` imports in that folder (see Verification).

## Verification

```bash
cd /home/schult_v/projects/redtape/apps/web
npx tsc --noEmit && npx eslint "src/**/*.{ts,tsx}"
npm test -- src/features/discovery-admin src/hooks src/services src/architecture.test.ts
npm run format:check
# measures
grep -rn "accessToken!\|candidateId!\|catalogueId!\|session!" src/features/discovery-admin --include=*.ts --include=*.tsx   # expect: no output
grep -rln "useLocale\|useAuth" src/features/discovery-admin/hooks                                                          # expect: useAdminQuery.ts, useDiscoveryAdminProbe.ts only
grep -n "features/\|contexts/" src/services/api.ts                                                                         # expect: no output
cd /home/schult_v/projects/redtape && ./ci.sh
```

`npm run build` (inside `./ci.sh`) type-checks the whole app; the lint script is `eslint "src/**/*.{ts,tsx}"`, the test script is `NODE_OPTIONS=--no-experimental-webstorage vitest run`.

## Parallel notes

- Runs beside **W2** (shared UI blocks). W2 owns `components/feedback`, `utils`, `features/auth`, and shared blocks inside `features/*/components`; W1 does not touch them except the seven import lines in discovery-admin components listed above. If W2 edits one of those same components, the chief of staff rebases W1; the hunks do not overlap.
- Runs beside A-, B-, I- and T-chapters, none of which touch `apps/web`, except **T3** (edits `apps/web/eslint.config.js` and `src/architecture.test.ts`). T3's rule W-A (shared code does not import `features/`) lists `src/services/api.ts:2` as a baseline entry that W1 removes: if T3 has merged, W1 deletes exactly that entry in `eslint.config.js` and in the test's baseline list and edits nothing else there; if not, T3 rebases and drops it. W1 also proves the result with the grep above.
- **W3** follows: it will split `types/index.ts` and derive unions from arrays using `defineListSpec`; keep `types/listControllers.ts` standalone so the split can move it. **W4** follows and restructures `CatalogueIndexPanel`, `DiscoveryDocumentPage`, `DiscoveryPipelinePage`.
- Files this chapter must not touch: `app/queryKeys.ts` (keys stay as they are), `architecture.test.ts` and `eslint.config.js` (except the single baseline entry above), `package.json`, lock files, anything under `apps/api`.
- Rollout inconsistency to report: the W1 `Touches` cell names `hooks`, `services`, `api.ts`, `web/hooks/`, but inlining the list-state wrappers necessarily edits containers and seven components (import lines) and adds `services/listQuery/spec.ts`; none intersects W2's or T3's files.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b refactor/admin-query-plumbing
```

```text
test(web): pin url, token and signed-out behaviour of the admin query hooks
refactor(web): add useAdminQuery and pass AdminAuth to the admin services
refactor(web): add defineListSpec and inline the list-state wrappers
refactor(web): move useApi out of the shared HTTP client
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.
