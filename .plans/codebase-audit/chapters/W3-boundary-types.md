---
name: "W3 — Boundary types"
overview: "Derive every string union from one array, split the 353-line discovery-admin types file per resource, validate suggestions URL params with typed oneOfFilter, and close the drift hole between API and web with an enum and field-set contract test (decision D1, no new dependency)."
todos:
  - id: characterize
    content: "Pin the unions, the spec keys and the suggestions URL behaviour before moving anything"
    status: pending
  - id: derive-unions
    content: "types/values.ts holds each array once; unions, sort keys and filter keys derive from it; listValues.ts and the duplicate arrays go"
    status: pending
  - id: split-types
    content: "Split types/index.ts per resource behind a re-export index"
    status: pending
  - id: suggestions-params
    content: "Typed oneOfFilter; useSuggestionFilters validates status and kind; one status array"
    status: pending
  - id: contract
    content: "Phase B (operator approved 2026-11-02, touches apps/api): OpenAPI snapshot, API freshness test, web enum and field-set contract test"
    status: pending
isProject: false
---

# W3 — Boundary types

**Repo:** `redtape` · **Branch:** `refactor/boundary-types` · **Status:** planned

**Depends on:** W1 (merged; this chapter builds on `defineListSpec` and `types/listControllers.ts`) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) section 5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `web/features/discovery-admin/types`, `web/services/listQuery`, suggestions and documents hooks (plus the files listed under Files that follow from deriving the unions).
**After:** W1.

**Findings:** T1, T2, T3. Decision D1 ([../gaps-and-decisions.md](../gaps-and-decisions.md)).

## Goal

Make a new backend value impossible to add on one side only, and stop trusting the URL.

- Every string union in `discovery-admin` and `suggestions` is declared once, as a `const` array; the type is `(typeof ARRAY)[number]`. Today each union exists twice (`types/index.ts` and `types/listValues.ts` or a spec file), plus loose copies.
- `types/index.ts` (353 lines, 81 files import it (80 inside the feature plus `test/discoveryAdminFixtures.ts`)) is split by resource without touching those importers.
- `?status=` and `?kind=` in the suggestions URL are validated against the arrays; an unknown value falls back instead of reaching the API.
- A contract test compares the web arrays and wire types with the API's OpenAPI schema (Phase B).

## Re-measured facts

| Audit claim | Source today |
| --- | --- |
| T1 `services/api.ts:79` returns `(await res.json()) as T` | True (line 79 before W1; the line moves after W1). The one `as T` of the shared client. |
| T1 "some wire fields are plain `string`" | Where the API types the field as `str`, the web type is correctly `string` and is not tightened here: `pipeline_stage` (`apps/api/app/schema/discovery/read.py:85`), `derived_stage` (`:223`), `DiscoveryRunRead.kind` and `.status` (`:170-171`), `EmitPreviewItemRead.kind` (`:208`). Tighten only after the API types them as enums (B3 owns `schema/discovery`); list them in the PR as "waiting for the API". Where the API has a `StrEnum` the web already has a union. |
| T2 each union declared twice | `DiscoverySource`, `DiscoveryTaskStatus`, `DiscoveryTaskKind`, `DiscoveryCandidateStatus`, `DiscoveryMentionRole` in `types/index.ts` and `types/listValues.ts`; sort-key unions (`TaskSortKey`, `CatalogueSortKey`, `CandidateSortKey`) in `types/index.ts` and `SORT_KEYS` in `services/{task,catalogue,candidate}ListQuery.ts`; `DocumentSortKey` in `documents/types/index.ts:27` and `documents/services/documentListQuery.ts:4-8` and again in `DocumentSortControl.tsx:9-17`. |
| (new) more copies | `PIPELINE_STAGES` (`listValues.ts:19`) is repeated as `STAGES` in `components/PipelineTimeline.tsx:5`; suggestion statuses exist as `SuggestionStatus` (`suggestions/types/index.ts:21`), `SuggestionStatusFilter` (`hooks/useSuggestionFilters.ts:3`) and the `STATUSES` array in `components/SuggestionsListView/SuggestionFilters.tsx:11`; `features/candidates/types/index.ts` declares `CandidateStatus = "staged" \| "emitted"` beside `DiscoveryCandidateStatus` (different feature and endpoint, left alone). |
| T3 `useSuggestionFilters.ts:19` casts | True: `(params.get("status") as SuggestionStatusFilter \| null) ?? "pending"`; `kind` is an unvalidated `string \| null` too. |
| "documents filters hooks" need `oneOfFilter` | **No.** `DOCUMENT_LIST_SPEC` already validates the sort key through the shared spec. The chips (`domain`, `group`, `situation` in `documents/utils/filterParams.ts`) are multi-valued taxonomy codes loaded from the API, not a closed enum, and `FilterValue` is single-valued by contract (`services/listQuery/types.ts`). Documents change only for T2 (`DocumentSortKey`). |
| `oneOfFilter` is typed | **No**: it returns `FilterValue \| undefined` (`services/listQuery/filters.ts`), so it cannot give a typed result to `useSuggestionFilters`. It also has no direct test. |

## Decision D1: runtime validation, generated types, or neither?

Checked: `apps/web/package.json` has no validator and no generator (`zod`, `valibot`, `openapi-typescript` are absent; `ajv` is in `node_modules` only as a transitive dependency of ESLint and must not be relied on). The API already exposes its schema: `app/main.py:47` uses `OpenAPIConfig(title="RedTape API", version="0.1.0")`, and Litestar's default controller (`litestar/openapi/controller.py`, `path = "/schema"`) serves `/schema/openapi.json`. Offline, `create_app().openapi_schema.to_schema()` yields 62 paths and 124 component schemas, including the enums `DiscoverySource`, `DiscoveryTaskKind`, `DiscoveryTaskStatus`, `DiscoveryCandidateStatus`, `DiscoveryMentionRole`, `DiscoveryArtifactKind`, `SuggestionKind`, `SuggestionStatus`, `SuggestionSource`, `UserRole`.

| Option | New dependency | Closes | Cost |
| --- | --- | --- | --- |
| A. Per-endpoint parsers (Zod-style) | `zod` or similar, runtime | Wrong shape at runtime | New runtime dependency; a third hand-written copy of every shape |
| B. Generated types from OpenAPI | `openapi-typescript` (devDependency) plus a committed `.d.ts` | Type drift at compile time | New tool, generation step in CI, large churn in 81 importers |
| C. Contract test over a committed OpenAPI snapshot, matcher written in the repo | none | Drift of enum values, and added, removed or renamed fields, at CI time | One snapshot file, one small matcher, one API-side freshness test |

**Recommendation: C**, matching gap D1's "contract tests now, generate clients when a third drift bug appears". It needs no dependency. The `as T` in `apiRequest` stays as the single, documented boundary cast (a comment states that shapes are guarded by the contract test, not at runtime). T1 is therefore closed as "guarded", not "validated at runtime"; say so in the PR. If the operator prefers A or B, that is a new dependency and a new decision, not part of this chapter.

Phase B touches `apps/api` (one script, one test) and a 100 KB-class JSON file; it is outside the rollout's W3 `Touches`; the operator approved it on 2026-11-02, and it is a separate PR if the chief of staff prefers. Phase A (everything else) stands alone.

## Files

All paths under `apps/web/src` unless noted.

### Phase A

| File | Change |
| --- | --- |
| `features/discovery-admin/types/values.ts` (+ `values.test.ts`) | New. Holds `DISCOVERY_SOURCES`, `TASK_STATUSES`, `TASK_KINDS`, `CANDIDATE_STATUSES`, `MENTION_ROLES`, `ARTIFACT_KINDS`, `PIPELINE_STAGES` (moved from `listValues.ts`, plus the two missing ones), and `TASK_SORT_KEYS`, `TASK_FILTER_KEYS`, `CATALOGUE_SORT_KEYS`, `CATALOGUE_FILTER_KEYS`, `CANDIDATE_SORT_KEYS`, `CANDIDATE_FILTER_KEYS`. Types derive: `export type DiscoverySource = (typeof DISCOVERY_SOURCES)[number]`, and so on. |
| `features/discovery-admin/types/listValues.ts` | Deleted. Its 8 importers (`services/{task,candidate,catalogue}ListQuery.ts`, `components/CatalogueSummaryChips.tsx`, `DiscoveryDocumentFilters.tsx`, `columns/{candidateFilters,catalogueColumns,taskColumns}`) import from `../types` (via the index). |
| `features/discovery-admin/types/index.ts` | Becomes `export * from "./task"` and so on (re-exports only, under 20 lines). The 81 importing files do not change. Plain `export *` lines work for the type-only files under `verbatimModuleSyntax`, and carry the runtime arrays of `values.ts`. |
| `features/discovery-admin/types/{task,catalogue,emit,coverage,budget,artifact,candidate,edge}.ts` | New; split below. |
| `features/discovery-admin/services/{task,candidate,catalogue}ListQuery.ts` | Take the sort and filter key arrays from `types`; `defineListSpec<TaskSortKey, TaskFilterKey>({ sortKeys: TASK_SORT_KEYS, filters: { … } })`, so a key in the array without a parser (or the reverse) fails `tsc`. `COMPLETE_CHOICES` (`candidateListQuery.ts`) moves to `values.ts` as `COMPLETE_CHOICES`. |
| `features/discovery-admin/components/PipelineTimeline.tsx` | Uses `PIPELINE_STAGES` instead of its own `STAGES`. |
| `services/listQuery/filters.ts` (+ new `filters.test.ts`) | `oneOfFilter<T extends string>(values: readonly T[]): (raw: string) => T \| undefined`. Still assignable to the spec's `(raw) => FilterValue \| undefined`. |
| `features/suggestions/types/values.ts` (new) and `types/index.ts` | `SUGGESTION_STATUSES`, `SUGGESTION_STATUS_FILTERS` (adds `"all"`, in the display order `pending, all, approved, rejected`), `SUGGESTION_KINDS`, `SUGGESTION_SOURCES`; `SuggestionStatus`, `SuggestionKind`, `SuggestionSourceType`, `SuggestionStatusFilter` derive from them. |
| `features/suggestions/hooks/useSuggestionFilters.ts` (+ test) | `status = oneOfFilter(SUGGESTION_STATUS_FILTERS)(params.get("status") ?? "") ?? "pending"`; `kind = oneOfFilter(SUGGESTION_KINDS)(params.get("kind") ?? "") ?? null`. No cast. `jurisdiction_id` stays a free string (a UUID the server resolves). |
| `features/suggestions/hooks/useSuggestionsListQuery.ts`, `components/SuggestionsListView/SuggestionFilters.tsx` | Import `SuggestionStatusFilter` from `../types`; `SuggestionFilters` iterates `SUGGESTION_STATUS_FILTERS` instead of its own `STATUSES`. |
| `features/documents/types/index.ts`, `services/documentListQuery.ts`, `components/DocumentsListView/DocumentSortControl.tsx` | `DOCUMENT_SORT_KEYS` once; `DocumentSortKey` derives; `DocumentSortControl.OPTIONS` keeps its labels and orders but is typed `Record<DocumentSortKey, …>`-shaped so a new key must get a label. |
| `services/api.ts` | One comment on the `as T` explaining the boundary (no behaviour change). |

Proposed split of `types/index.ts` (names verified against the file; line numbers are today's):

| New file | Types | Source lines (approx., today's file) |
| --- | --- | --- |
| `values.ts` | the six enum unions and the six sort/filter key unions (now derived), arrays | 5-17, 38-44, 66-69, 136-137, 175-192 |
| `task.ts` | `DiscoveryTask`, `DiscoveryTaskListResponse` | 19-36, 46-51 |
| `catalogue.ts` | `CatalogueServiceSummary`, `CatalogueSummaryChips`, `CatalogueListResponse`, `CataloguePipelineResponse` | 53-64, 82-104 |
| `emit.ts` | `EmitPreviewItem`, `EmitPreviewResponse`, `DiscoveryEmitConflict`, `CandidateEmitSuggestion`, `CandidateEmitPreview` | 71-80, 330-353 |
| `coverage.ts` | `DiscoveryTaskCounts`, `DiscoveryCandidateCounts`, `DiscoveryRun`, `DiscoveryArtifactTotals`, `DiscoveryArtifactCoverage`, `DiscoveryLlmOutcomes`, `DiscoveryCoverageResponse` | 106-173 |
| `budget.ts` | `DiscoveryBudget`, `DiscoveryBudgetsResponse` | 245-260 |
| `artifact.ts` | `DiscoveryArtifact`, `DiscoveryArtifactListResponse`, `DiscoveryMentionArtifact` | 223-243, 261-267 |
| `candidate.ts` | `DiscoveryCandidateRecord`, `DiscoveryCandidate`, `DiscoveryCandidateListResponse`, `DiscoveryCandidateMention`, `DiscoveryTagSupport`, `DiscoveryCandidateDetailResponse` | 193-222, 268-306 |
| `edge.ts` | `DiscoveryCandidateEdge`, `DiscoveryCandidateEdgesResponse` | 307-329 |
| `listControllers.ts` | from W1, unchanged | n/a |

No resulting file exceeds about 70 lines; the split follows API resources (one response model family per file), not a line target. `CataloguePipelineResponse.entities/fetch_logs/claims/events` stay `Record<string, unknown>[]` until B3 publishes typed read models (`PipelineEntityRow` and siblings, [audit section 5](../00-audit-report.md)); if B3 is already merged, mirror them in `catalogue.ts` and add them to the contract test.

### Phase B (operator approved 2026-11-02)

| File | Change |
| --- | --- |
| `apps/api/scripts/export_openapi.py` | New. Writes `create_app().openapi_schema.to_schema()["components"]["schemas"]` as sorted, indented JSON to `apps/web/src/test/contract/openapi.schemas.json`; has a docstring and passes the API's ruff and mypy. |
| `apps/api/tests/test_openapi_snapshot.py` | New. Regenerates the schemas and fails with the regenerate command when they differ from the committed file (negative path: a stale snapshot). |
| `apps/web/src/test/contract/openapi.schemas.json` | New, generated. |
| `apps/web/src/test/contract/schemaMatch.ts` (+ `.test.ts`) | New. `enumValues(name)` and `propertyNames(name)` over the snapshot; `$ref`, `allOf` and nullable `anyOf` resolved only as far as the property-name check needs. About 40 lines, no dependency. |
| `apps/web/src/test/contract/contract.test.ts` | New. Enum coverage and field-set checks (below). |

## TDD loop

### Red

Characterisation first (green before and after every step):

1. `types/values · unions are exactly today's` with `expectTypeOf<DiscoverySource>().toEqualTypeOf<"govdata" | "pvog" | "fim" | "leika" | "manual">()` and the same for `DiscoveryTaskStatus`, `DiscoveryTaskKind`, `DiscoveryCandidateStatus`, `DiscoveryMentionRole`, `TaskSortKey`, `CatalogueSortKey`, `CandidateSortKey`, `TaskFilterKey`, `CandidateFilterKey`, `CatalogueFilterKey`, `DocumentSortKey`, `SuggestionStatus`. Type assertions run under `tsc --noEmit`, so the Verification command catches a changed union. Runtime half: `values · no array repeats a value` (each array against `new Set`).
2. The existing `taskListQuery.test.ts`, `candidateListQuery.test.ts`, `catalogueListQuery.test.ts`, `listQuery.test.ts` stay unchanged and green.
3. `useSuggestionFilters` existing three tests stay green.

New behaviour, failing today:

4. `oneOfFilter · accepts a listed value and returns it typed`, `· rejects an unlisted value`, `· rejects the empty string`, `· is case sensitive` (negative paths).
5. `useSuggestionFilters · an unknown status falls back to pending` (`?status=bogus`), `· status=all is kept`, `· an unknown kind is null` (`?kind=bogus`), `· a known kind is kept`, `· setStatus keeps an unknown kind out of the URL`.
6. `SuggestionsListPage · a bad ?status= requests pending` (extends `SuggestionsListPage.test.tsx`; asserts the `/api/v1/suggestions` call carries `status=pending`, not `bogus`).
7. `SuggestionFilters · renders one chip per status filter in order` (`pending, all, approved, rejected`).
8. `PipelineTimeline · renders one badge per pipeline stage and highlights the derived one` (no test today; pins the array change).
9. `list specs · declare a parser for every filter key and accept every sort key` (table over the three admin specs and `DOCUMENT_LIST_SPEC`; fails if an array and a spec diverge).
10. Phase B: `contract · web arrays equal the API enums` (`it.each` over `DISCOVERY_SOURCES`↔`DiscoverySource`, `TASK_STATUSES`↔`DiscoveryTaskStatus`, `TASK_KINDS`↔`DiscoveryTaskKind`, `CANDIDATE_STATUSES`↔`DiscoveryCandidateStatus`, `MENTION_ROLES`↔`DiscoveryMentionRole`, `ARTIFACT_KINDS`↔`DiscoveryArtifactKind`, `SUGGESTION_STATUSES`↔`SuggestionStatus`, `SUGGESTION_KINDS`↔`SuggestionKind`, `SUGGESTION_SOURCES`↔`SuggestionSource`); `contract · a typed fixture has exactly the API's fields` for each wire type that has a fixture (start with `DiscoveryTask`↔`DiscoveryTaskRead`, `CatalogueServiceSummary`↔`CatalogueServiceRead`, `DiscoveryRun`↔`DiscoveryRunRead`, `DiscoveryCoverageResponse`, `DiscoveryTaskListResponse`, `CatalogueListResponse`, `CatalogueSummaryChips`; extend to the candidate, mention, edge, artifact and budget types using `test/discoveryAdminFixtures.ts`); `schemaMatch · reports a missing and an extra field` and `· reports an enum value that is not in the web list` (negative, on tiny inline schemas). API side: `test_openapi_snapshot · matches the committed file`, `· fails with the regenerate command when stale`.

Run `npm test -- src/features/discovery-admin src/features/suggestions src/features/documents src/services src/test` and `npx tsc --noEmit`; confirm 4-9 fail (and 10 once Phase B starts), 1-3 pass.

### Green

Each step is a commit; moves before logic.

1. Add `values.ts` and make the unions derive. Delete `listValues.ts`; repoint its 8 importers; delete the sort-key arrays in the services. `tsc` is the guide.
2. Split `types/index.ts` into the resource files; make `index.ts` re-export.
3. Type `oneOfFilter`; add the suggestions arrays and the validated hook; drop the two duplicate arrays; use `PIPELINE_STAGES` in `PipelineTimeline`; derive `DocumentSortKey`.
4. Phase B (approved): snapshot, API test, matcher, contract test. If a real drift shows up (a web field the API does not have, or a missing enum member), fix the web type in the same PR and list it; if the API is wrong, open a note for B3 and mark the test `it.fails` with the reason rather than silencing it.

### Refactor

Judge by responsibility. Check that `values.ts` holds only constants and their derived types (no helpers), that each resource file is "one response family" describable without "and", and that no re-export was added only to rename. Apply the rule of three to enum label tables if W2's optional enum-label commit has landed (do not merge them into `values.ts`: labels are UI, values are wire). No `any`, no `as` (except the one documented boundary cast in `api.ts`), no `@ts-ignore`. Report `Refactor gate: smells found -> …, refactorings applied -> …` with before and after numbers: lines of `types/index.ts` (353 to under 20), string unions declared twice (count from `grep -c "satisfies readonly" src/features/discovery-admin/types/listValues.ts src/features/discovery-admin/services/*ListQuery.ts`, 9 today, to 0), `as` casts in `features/suggestions` (1 to 0).

## Verification

```bash
cd /home/schult_v/projects/redtape/apps/web
npx tsc --noEmit && npx eslint "src/**/*.{ts,tsx}"
npm test -- src/features/discovery-admin src/features/suggestions src/features/documents src/services src/test src/architecture.test.ts
npm run format:check
# measures
wc -l src/features/discovery-admin/types/*.ts
grep -rn "listValues" src                                                         # expect: no output
grep -rn "as SuggestionStatusFilter\| as .*Filter\b" src/features/suggestions      # expect: no output
# Phase B only
cd /home/schult_v/projects/redtape/apps/api && uv run python scripts/export_openapi.py && git diff --stat -- ../web/src/test/contract
uv run pytest tests/test_openapi_snapshot.py && uv run ruff check . && uv run mypy app scripts
cd /home/schult_v/projects/redtape && ./ci.sh
```

## Parallel notes

- **W3 runs in batch 2, after W1 and beside B3, B4, I1, I2, W4 and the T1 slices.** W3 must not edit `features/discovery-admin/{containers,components}` beyond the import lines and the `PipelineTimeline.tsx` constant: **W4** owns them (W4 starts after W1 and W2, so it can run beside W3; rebase whichever merges second). W3 must not touch `features/discovery-admin/hooks` or `services/*Api.ts` (W1) nor `components/feedback`, `utils`, `features/auth` (W2).
- **B3** owns `apps/api/app/schema/discovery`: if B3 retypes `pipeline_stage` or the pipeline rows first, mirror them in `catalogue.ts` and the contract test; if not, leave them. Phase B must not edit `apps/api/app`, only add the script and the test. **B6** edits `apps/api/scripts/`; `export_openapi.py` is a new file there, no overlap.
- **G1** and **G2** run after: G1 relies on `oneOfFilter` and `values` tests added here and does not repeat them; G2 verifies the Phase B snapshot test is part of `./ci.sh` (the API `pytest` run picks it up).
- Files this chapter must not touch: `app/queryKeys.ts` (W2 changes `suggestions.list`), `architecture.test.ts`, `eslint.config.js` (T3), `package.json` and lock files, `apps/api/app/**`.
- Core-doc inconsistency to report: the rollout's W3 `Touches` omits the suggestions and documents component and type files and, for Phase B, `apps/api/{scripts,tests}`.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b refactor/boundary-types
```

```text
test(web): pin the discovery-admin unions and the suggestions URL fallbacks
refactor(web): derive every discovery-admin union from one array
refactor(web): split the discovery-admin types file per resource
fix(web): validate the suggestions status and kind params in the URL
test: pin enums and field sets of the web types against the OpenAPI snapshot   (Phase B)
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.
