---
name: "W4 — Admin containers"
overview: "The two admin drill-down pages run one query each; their panels become small section containers that own their queries and take an id; DocumentDetail and PipelineDetail take data plus children; one filter-capability builder replaces three ways of building a column filter."
todos:
  - id: characterize
    content: "Pin secondary-panel failure isolation and the request pattern of both drill-down pages"
    status: pending
  - id: section-containers
    content: "Section containers own the edges, evidence, emit-preview and tag queries; pages run one query; Detail components take data and children"
    status: pending
  - id: filter-capability
    content: "One filterCapability builder for task, catalogue and candidate columns; taskColumns keeps one responsibility"
    status: pending
isProject: false
---

# W4 — Admin containers

**Repo:** `redtape` · **Branch:** `refactor/admin-containers` · **Status:** planned

**Depends on:** W1, W2 (both merged) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) L9 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `web/features/discovery-admin/{containers,components}`.
**After:** W1, W2.

**Findings:** L9, and the column-definition duplication behind the "taskColumns split" item.

## Goal

Layering and prop-count cleanup, behaviour-preserving, including request timing: the secondary queries keep loading in parallel with the main one (operator decision, 2026-11-02).

- `DiscoveryDocumentPage` (69 lines, 5 queries, 4 prop-slots) and `DiscoveryPipelinePage` (88 lines, 3 queries, two `ReactNode`-returning helpers) run **one** query each and compose.
- Each secondary panel gets a small container that owns its query and takes an id: it is the only place the query hook, `toQueryStatus` and the presentational panel meet.
- `DocumentDetail` (5 props) and `PipelineDetail` (3 props, two of them slots) take `data` plus `children`.
- One `filterCapability` builder replaces the three ways columns declare a filter today.

## Re-measured facts

| Claim | Source today |
| --- | --- |
| L9 `DiscoveryDocumentPage` runs 5 queries and builds 4 prop-slots | `containers/DiscoveryDocumentPage.tsx`: `useDiscoveryCandidateQuery`, `useDiscoveryCandidateArtifactsQuery`, `useDiscoveryCandidateEmitPreviewQuery`, `useCandidateEdgesQuery`, plus `useTagNames` (two taxonomy queries inside); slots `tags`, `edges`, `emit`, `evidence` into `DocumentDetail`. |
| `DiscoveryPipelinePage` runs 3 queries with two `ReactNode` helpers | True: `useDiscoveryPipelineQuery`, `useDiscoveryEmitPreviewQuery`, `useDiscoveryArtifactsQuery`; helpers `previewPanel` and `artifactsPanel`; a `pipelineView` union with four arms. |
| The page re-implements 404 detection | `DiscoveryDocumentPage.tsx:20-22` defines a local `isNotFound` over `ApiRequestError`; `services/apiErrors.ts` already exports `isNotFound`. |
| Prop counts | `DocumentDetail` 5 (`data, tags, edges, emit, evidence`), `PipelineDetail` 3, `DocumentTagsPanel` 4 (`domains, situations, domainNames, situationNames`); `DocumentEmitPanel`, `DocumentEdgesPanel` 3 each, `ArtifactsPanel` and `EmitPreviewPanel` 2. |
| "taskColumns split" | `components/columns/taskColumns.tsx` is 97 lines, one function building eight column objects in a straight list: one responsibility. What has a second responsibility is the local `filterOf` (filter capability construction). The same job is done three ways: `taskColumns.filterOf`, `candidateFilters.capability` (with a `CapabilitySpec` and an `operator` default) and inline literals in `catalogueColumns.tsx:56-60,68-72`. |
| `DiscoveryCoveragePage` | Already composed (two queries, a `BudgetsSection` that isolates the budgets failure); not part of this chapter. |

## Design

| Decision | Choice | Why |
| --- | --- | --- |
| Where do the section containers live? | `containers/`, flat, named `<Thing>Section.tsx`. | `apps/web/CLAUDE.md`: containers wire hooks to components; components stay presentational. `architecture.test.ts` only checks `components/**` for feature `services/` imports and for inline query keys, so section containers importing hooks are within the rules. No new folder. |
| How do the Detail components receive the panels? | `DocumentDetail({ data, children })`, `PipelineDetail({ data, children })`; the page passes the sections as children in the order it wants. | 2 props; no `ReactNode` slot props; the fixed render order moves to the page, where the composition is visible. |
| Request timing | **Unchanged: parallel.** The operator wants parallel loading (2026-11-02). The page keeps one `useQuery` for the main record and calls one prefetch hook, `usePrefetchDocumentSections(candidateId)` (and `usePrefetchPipelineSections(catalogueId)`), that starts the secondary requests on mount with `queryClient.prefetchQuery` and the same query keys and functions as the section containers. The sections then read the warm cache when they mount after the main data arrives. | The ids come from the route, so nothing waits for the main query. Section containers still own their queries (retry refetches only that panel) and take an id. To avoid duplicating each query's key and function, each section hook exports a `queryOptions` factory (`edgesQueryOptions(auth, locale, id)` and so on), used by both the hook and the prefetch. If W1's `useAdminQuery` does not already expose that factory, W4 adds it there (W1 is merged first). A 404 candidate still fires the secondary requests, exactly as today; that is accepted. |
| Tags | `DocumentTagsSection({ data })` calls `useTagNames()` and renders `DocumentTagsPanel`. The panel keeps its 4 props (`domains`, `situations`, `domainNames`, `situationNames`) unless grouping them into `{ supports, names }` per axis keeps `DocumentTagsPanel.test.tsx` readable; if not, record it in the PR as an accepted exception to the 3-prop guideline. | The names lookup is the only extra input; the clump is real but small, and the guideline is a guideline (`apps/web/CLAUDE.md`). |

## Files

All paths under `apps/web/src/features/discovery-admin`.

| File | Change |
| --- | --- |
| `containers/DocumentTagsSection.tsx` | New. Takes `data: DiscoveryCandidateDetailResponse`; uses `useTagNames`; renders `DocumentTagsPanel`. |
| `containers/DocumentEdgesSection.tsx` | New. Takes `candidateId`; `useCandidateEdgesQuery`; renders `DocumentEdgesPanel` with `toQueryStatus`. |
| `containers/DocumentEvidenceSection.tsx` | New. Takes `candidateId`; `useDiscoveryCandidateArtifactsQuery`; renders `ArtifactsPanel`. |
| `containers/DocumentEmitSection.tsx` | New. Takes `candidateId` and `suggestionId` (2 props); `useDiscoveryCandidateEmitPreviewQuery`; renders `DocumentEmitPanel`. |
| `containers/PipelineArtifactsSection.tsx`, `containers/PipelinePreviewSection.tsx` | New. Take `catalogueId`; `useDiscoveryArtifactsQuery` / `useDiscoveryEmitPreviewQuery`; render `ArtifactsPanel` / `EmitPreviewPanel`. |
| `containers/DiscoveryDocumentPage.tsx` (69 lines) | One query. `isNotFound` comes from `services/apiErrors`; the loading branch uses `QueryBoundary` and `loadingUntilData` (W2, W1 era). Composes `DocumentDetail` with the four sections as children. |
| `containers/DiscoveryPipelinePage.tsx` (88 lines) | One query. `QueryBoundary` replaces `PipelineLoading` and the error arm; the remaining arms are missing and ready. `pipelineView`, `previewPanel`, `artifactsPanel` are deleted. |
| `components/DocumentDetail.tsx`, `components/PipelineDetail.tsx` | Props `data` and `children`; they render children after their own content. |
| `components/columns/filterCapability.ts` (+ test) | New. `filterCapability({ key, label, options, operator = "eq" })`, moved from `candidateFilters.ts` (`capability` and `CapabilitySpec`). |
| `components/columns/candidateFilters.ts`, `taskColumns.tsx`, `catalogueColumns.tsx` | Use `filterCapability`; `taskColumns` loses `filterOf`; `catalogueColumns` loses its two inline literals. |
| `components/DocumentTagsPanel.tsx` | Optional prop reduction (see Design). |

Files that stay as they are: `DocumentEdgesPanel`, `DocumentEmitPanel`, `EmitPreviewPanel`, `ArtifactsPanel` (W2 already moved their loading and error branches into `QueryBoundary`; they stay presentational and receive `status` plus data).

## TDD loop

### Red

Characterisation (green before and after every step). The existing integration tests are the safety net and stay unchanged: `DiscoveryDocumentPage.test.tsx` (12 cases), `DiscoveryPipelinePage.test.tsx` (3), `taskColumns.test.tsx` (6), `candidateColumns.test.tsx` (7), `DocumentTagsPanel.test.tsx` (2). Add before refactoring:

1. `DiscoveryDocumentPage · keeps the document visible when only the edges fail to load` and `· when only the emit preview fails` and `· when only the artifacts fail` (each: the failing panel shows a "Try again" button, header and mentions still render, the other panels render). Negative paths, pass today.
2. `DiscoveryDocumentPage · the retry of a failed panel refetches only that panel` (click retry, only the matching endpoint is requested again).
3. `DiscoveryPipelinePage · keeps the pipeline visible when only the emit preview fails` (mirror of the existing artifacts case).
4. `DiscoveryDocumentPage · a missing candidate shows the not-found view` (existing coverage? check; add if absent) and `· a server error on the candidate shows retry`.

New behaviour, failing today:

5. `DiscoveryDocumentPage · requests the edges, artifacts and emit preview while the candidate request is still pending`: hold the candidate response, assert all three secondary endpoints were already requested (passes today, and must keep passing after the sections are extracted; this pins the parallel loading). Same for `DiscoveryPipelinePage · requests artifacts and emit preview while the pipeline request is pending`. Add `· each secondary endpoint is requested once` to prove the prefetch and the section share one cache entry.
6. Section containers: `DocumentEdgesSection · loads the edges of its candidate id and renders them`, `· shows retry inside the panel when the request fails` (and nothing from the other sections); `DocumentEmitSection · an emitted candidate shows the emitted state` (`suggestionId` set) and `· a staged candidate shows the preview`; `DocumentEvidenceSection`, `PipelineArtifactsSection`, `PipelinePreviewSection`, `DocumentTagsSection` with one happy and one failure case each. Each renders through `renderWithProviders` with a stubbed `fetch`; each fails today because the file does not exist.
7. `filterCapability · defaults to the eq operator`, `· keeps an explicit gte operator`, `· passes options through` (pure); `taskColumns · declares the kind, status and source filters with the translated labels` (characterisation of what `filterOf` produced; extend the existing task test).
8. Architecture guard check (no new rule file edit): `grep` in Verification proves no `components/` file imports a hook that calls the network. `architecture.test.ts` stays untouched (T3 owns it).

Run `npm test -- src/features/discovery-admin/containers src/features/discovery-admin/components` and confirm 6-7 fail (the new section containers and `filterCapability` do not exist yet), while 1-5 and the existing cases pass.

### Green

1. Extract the section containers one at a time (edges, evidence, emit, tags; then pipeline artifacts and preview), each by moving the hook call and the `toQueryStatus` wiring out of the page and exporting its `queryOptions` factory. Add the two prefetch hooks last, so the parallel-loading test (5) stays green after every commit. Commit per pair.
2. Change `DocumentDetail` and `PipelineDetail` to `data` plus `children`; rewrite the two pages to compose. Delete the helper functions.
3. Add `filterCapability`; switch the three column files.

### Refactor

Judge by responsibility, not lines. A section container is describable as "loads X for an id and shows it"; if one grows a second job, split it. Check the pages: one query, one boundary, one composition, one nesting level. Check no section re-implements loading or error branches (W2's `QueryBoundary` does). Apply the rule of three to the two artifacts sections: they differ in hook only, two sites, so no shared abstraction. Confirm `taskColumns.tsx` stays a straight list (do not split it into per-column files to shorten it; the audit's "split" is satisfied by moving the filter construction out). No `any`, no `as`, no `!`. Report `Refactor gate: smells found -> …, refactorings applied -> …` with before and after numbers: queries per page (document 5 to 1, pipeline 3 to 1), props of `DocumentDetail` (5 to 2) and `PipelineDetail` (3 to 2), lines of the two pages (69 and 88), ways to build a filter capability (3 to 1).

## Verification

```bash
cd /home/schult_v/projects/redtape/apps/web
npx tsc --noEmit && npx eslint "src/**/*.{ts,tsx}"
npm test -- src/features/discovery-admin src/architecture.test.ts
npm run format:check
# measures
grep -c "use.*Query(" src/features/discovery-admin/containers/DiscoveryDocumentPage.tsx src/features/discovery-admin/containers/DiscoveryPipelinePage.tsx   # expect: 1 each
grep -rn "ReactNode" src/features/discovery-admin/components/DocumentDetail.tsx src/features/discovery-admin/components/PipelineDetail.tsx                  # expect: only children
grep -rln "from \"../hooks/use.*Query\"" src/features/discovery-admin/components                                                                             # expect: no output
cd /home/schult_v/projects/redtape && ./ci.sh
```

## Parallel notes

- **W4 runs in batch 2 beside B2-B4, I1, I2, W3 and the T1 slices.** Of the web chapters only **W3** is concurrent: W3 edits `features/discovery-admin/types`, the `*ListQuery.ts` services and the import lines of `components/columns/{candidateFilters,catalogueColumns,taskColumns}` (the `listValues` imports) and `PipelineTimeline.tsx`. W4 also edits the three column files (filter construction). Keep each hunk small and rebase on whichever merged first; do not reformat imports.
- W4 must not touch `features/discovery-admin/hooks` or `services` (W1), `components/feedback`, `utils`, `features/auth` (W2), `types/**` (W3), `architecture.test.ts` and `eslint.config.js` (T3), `app/queryKeys.ts`.
- **G1** follows (after W3 and W4): it will not repeat the section and page tests added here, and adds the remaining direct unit tests for `safeHttpUrl`, `hostOf`, `localizedTitle`, `translateOrRaw` if still missing.
- Rollout inconsistency to report: the W4 `Touches` cell lists `containers` and `components`, but the section containers are new files in `containers/` and the filter builder is a new file in `components/columns/`; the W3 overlap above is real for the three column files.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b refactor/admin-containers
```

```text
test(web): pin panel failure isolation on the document and pipeline pages
refactor(web): move the secondary queries of the drill-down pages into section containers
refactor(web): one filterCapability builder for the admin column filters
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.
