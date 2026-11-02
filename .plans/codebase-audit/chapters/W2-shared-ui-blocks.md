---
name: "W2 — Shared UI blocks"
overview: "One QueryBoundary replaces the repeated loading/error branches (with role=status), one relative-time util replaces two near-clones, one auth-status lookup feeds both guards; dead component removed, small consistency fixes."
todos:
  - id: characterize
    content: "Pin the panels, the two time formatters and both guards before moving anything"
    status: pending
  - id: query-boundary
    content: "QueryBoundary + LoadingNote in components/feedback; four panels adopt it; delete the dead DiscoveryCatalogueQueryStatus"
    status: pending
  - id: relative-time
    content: "Shared utils/relativeTime.ts replaces formatRetryAfter and suggestions/utils/formatRelativeTime"
    status: pending
  - id: shared-chips
    content: "Move CompletenessChips to components/data-display (removes the last cross-feature component import of discovery-admin)"
    status: pending
  - id: auth-gate
    content: "Shared authGate lookup for RequireAuth and the discovery admin guard; remove the role cast"
    status: pending
  - id: consistency
    content: "EMPTY_VALUE, single FilterOption, Record casts, queryKeys.suggestions.list object parameter"
    status: pending
  - id: enum-labels
    content: "Last commit: translate source and status values via translateOrRaw (operator approved the new strings and the API seed change on 2026-11-02)"
    status: pending
isProject: false
---

# W2 — Shared UI blocks

**Repo:** `redtape` · **Branch:** `refactor/shared-ui-blocks` · **Status:** planned

**Depends on:** none (W1 only for the `useApi` move, which this chapter does not need) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `web/components/feedback`, `web/utils`, `web/features/auth`, `web/features/*/components` (shared blocks).
**After:** none.

**Findings:** D12, D13, D14, dead code, web consistency items.

## Goal

Behaviour-preserving, with two deliberate changes (loading text gets `role="status"`; `RequireAuth` ranks `admin`) and one optional visible change (translated enum labels, last commit). After the chapter:

- Loading and error branches of four panels live in one `QueryBoundary`; no live `<Text>{t("common.loading")}</Text>` without `role="status"` remains in panels.
- One `utils/relativeTime.ts` owns "coarsest whole unit"; `formatRetryAfter.ts` and `suggestions/utils/formatRelativeTime.ts` are deleted; no feature imports another feature's `utils` for time formatting.
- `RequireAuth` and the discovery admin guard read one `AuthStatus` lookup; the `role as MinRole` cast is gone, and `admin` is ranked (a latent bug fix, red test first).
- `DiscoveryCatalogueQueryStatus.tsx` (no importer) is deleted; `CompletenessChips` is shared, so no `discovery-admin` file imports a component of another feature.
- One `FilterOption`, one empty-value placeholder, no `as Record<string, number>` casts, `queryKeys.suggestions.list` with at most 3 parameters.

## Re-measured facts (differences from the audit in bold)

| Audit claim | Source today |
| --- | --- |
| Loading text lacks `role="status"` on 6 of 7 sites | **5 live sites** render a bare `<Text>{t("common.loading")}</Text>`: `components/DocumentEdgesPanel.tsx:24`, `DocumentEmitPanel.tsx:21`, `EmitPreviewPanel.tsx:19`, `containers/DiscoveryPipelinePage.tsx:33`, `containers/DiscoveryDocumentPage.tsx:36`. The only text site with `role="status"` is the dead `DiscoveryCatalogueQueryStatus.tsx:18`. `ArtifactsSkeleton`, `DiscoveryAdminLoading` and `DataTableStateView` already announce. |
| `taskColumns.tsx:3` imports from suggestions by relative path | True; also `candidateColumns.tsx:2` and `features/candidates/components/CandidateDetailView/CandidateScreenshot.tsx:5`. `formatRelativeTime` therefore has **three** feature consumers plus `suggestions` itself (`SuggestionCard.tsx`, `SuggestionDetailHeader.tsx`). |
| `RequireAuth` and the admin guard disagree on `unconfigured` | True and **intentional and tested**: `RequireAuth.test.tsx:114` expects the not-found view; `RequireDiscoveryAdmin.test.tsx:147` expects the "auth not configured" message. Keep both views; share the status lookup. **Also found:** `RequireAuth` has no consumer outside its own test (`grep -rn RequireAuth src` finds no route; `docs/planning/STATUS.md:71` lists it as delivered), so only the admin guard is live. Keep it (operator call: delete it if the generic guard is not wanted) and fix its role table. |
| Empty placeholder `"—"` vs `"-"` | `"—"`: `columns/mentionColumns.tsx:40,51`, `columns/candidateColumns.tsx:44`; `"-"`: `coverage/runGroups.ts:28,35`. The i18n strings `discovery_admin.tasks.retry_none` and `lease_none` are also `"—"`. |
| Raw enum values at `taskColumns.tsx:51,59` and `candidateFilters.ts:62` | **Lines drifted**: `taskColumns.tsx:53` (`task.kind`), `:67` (`task.source`), status in `cells/TaskStatusCell.tsx`, `candidateFilters.ts:60`. Also `catalogueColumns.tsx:59,61` and `DiscoveryDocumentFilters.tsx:17`. |
| Hard-coded "Redtape" in `LoadingShell.tsx:30` | True (line 30) but **not worth a change**: it is a proper noun, the shell renders before the i18n bundle, `BrandMark` is an SVG with no text, and a constant would have one consumer (rule of three). Dropped; record as "declined" in the PR. |
| Duplicate `FilterOption` | `components/data-display/DataTable/types.ts:16` and `features/discovery-admin/components/FilterSelect.tsx:3` (same two fields). |
| `as Record<string, number>` casts | `coverage/contentGroups.ts:30` and `coverage/runGroups.ts:21`. |
| `suggestions.list` takes 4 positional params | `app/queryKeys.ts` (`suggestions.list`); one caller, `features/suggestions/hooks/useSuggestionsListQuery.ts:28`. |
| Cross-feature component import (T3 baseline) | `features/discovery-admin/components/columns/cells/CandidateReadinessCell.tsx:1` imports `candidates/components/CompletenessChips`; the component takes only `flags` and a label prefix, and is used by two features, so it belongs in `components/data-display`. |
| Dead component | `grep -rn DiscoveryCatalogueQueryStatus` over the repo finds only the file itself and two plan documents. Re-run at the start; delete only if still true. |

## Files

All paths under `apps/web/src` unless noted.

| File | Change |
| --- | --- |
| `components/feedback/QueryBoundary.tsx` (+ test), `components/feedback/LoadingNote.tsx` | New. `QueryBoundary({ status, loading?, children })` (3 props): `status.isLoading` renders `loading ?? <LoadingNote />`, `status.isError` renders `<QueryError onRetry={status.onRetry} />`, otherwise `children`. `LoadingNote` is `<Text role="status">{t("common.loading")}</Text>`. Not a re-use of the dead component: that one takes a hand-built `state` string beside `onRetry`, the live code already has a `QueryStatus` object. |
| `features/discovery-admin/components/{DocumentEdgesPanel,DocumentEmitPanel,EmitPreviewPanel,ArtifactsPanel}.tsx` | Wrap their body in `QueryBoundary`. `ArtifactsPanel` passes `loading={<ArtifactsSkeleton />}` and its `panelState` loses the `loading` and `error` cases. `DocumentEmitPanel` keeps the `suggestionId` check first (an emitted candidate never shows loading). |
| `features/discovery-admin/components/DiscoveryCatalogueQueryStatus.tsx` | Deleted. |
| `utils/relativeTime.ts` (+ test) | New shared folder `src/utils` (does not exist yet; the rollout's `web/utils` touch implies it). Exports `formatRelativeTime(iso, locale, now?)` (past, same signature and output as today) and `formatTimeUntil(iso \| null, locale, now?)` (future, same output as `formatRetryAfter`), built on one `pickUnit`. Add one line for `utils/` to the layer tree in `apps/web/CLAUDE.md`. |
| `features/suggestions/utils/formatRelativeTime.ts` (+ test), `features/discovery-admin/utils/formatRetryAfter.ts` (+ test) | Deleted after their cases move into `utils/relativeTime.test.ts`. |
| Import sites | `features/suggestions/components/SuggestionsListView/SuggestionCard.tsx`, `SuggestionDetailView/SuggestionDetailHeader.tsx`, `features/candidates/components/CandidateDetailView/CandidateScreenshot.tsx`, `features/discovery-admin/components/columns/{taskColumns,candidateColumns}.tsx`. |
| `features/auth/types/authGate.ts` (+ test) | New. Lives in `types/` because T3's rule W-B lets other features import only `<feature>/types/**`, `auth/contexts/**` and `taxonomy/hooks/**`; `auth/utils/` would be a new violation, and the `types/listValues.ts` precedent shows runtime constants already sit in `types/`. `AUTH_GATE: Record<AuthStatus, "wait" \| "login" \| "unconfigured" \| "open">` (`loading`, `anonymous`, `unconfigured`, `authenticated`). |
| `features/auth/components/RequireAuth.tsx` | `guardOutcome` reads `AUTH_GATE`; `unconfigured` still maps to `"hidden"`. `MinRole` becomes `(typeof ROLES)[number]` over `ROLES = ["user", "moderator", "admin"] as const` (mirrors the API `UserRole` in `apps/api/app/models/user.py`, whose rank order is the same); rank is `ROLES.findIndex((r) => r === role)` (negative means unknown role, still `"wait"`), so `ROLE_RANK` and `role as MinRole` disappear. **Fixes a latent bug:** today `admin` is missing from `ROLE_RANK`, so an admin user gets `"wait"` (blank page) on a moderator route. |
| `features/discovery-admin/utils/discoveryAdminGuardOutcome.ts` | `authOutcomes` / `authGuardOutcome` replaced by `AUTH_GATE`; `unconfigured` still maps to `"auth-unconfigured"`. |
| `utils/emptyValue.ts` | New `EMPTY_VALUE = "—"`; used by `columns/mentionColumns.tsx`, `columns/candidateColumns.tsx`, `coverage/runGroups.ts`. `runGroups.ts` therefore changes its `"-"` to `"—"` (visible, intended). |
| `components/data-display/CompletenessChips/{CompletenessChips,FlagChip}.tsx`, `index.ts`, `CompletenessChips.test.tsx` | Moved with `git mv` from `features/candidates/components/CompletenessChips/` (first commit, no logic change). `CompletenessFlags` moves next to it and `features/candidates/types/index.ts` re-exports it, so no importer of the type changes. Importers: `candidates/.../CandidateChecklist.tsx` and `discovery-admin/.../columns/cells/CandidateReadinessCell.tsx` (the T3 baseline row `CandidateReadinessCell.tsx:1`, which T3 assigns to "W2 or W4"; W2 takes it). |
| `features/discovery-admin/components/FilterSelect.tsx` | Import `FilterOption` from `components/data-display/DataTable` instead of redeclaring it. |
| `coverage/metricModel.ts` (`countRows`), `coverage/contentGroups.ts`, `coverage/runGroups.ts` | `countRows` accepts `Partial<Record<string, number>>` and skips `undefined`; both casts go. |
| `app/queryKeys.ts`, `features/suggestions/hooks/useSuggestionsListQuery.ts` | `suggestions.list(filters: { status; kind; jurisdictionId }, locale)`. Key array shape unchanged. |
| Optional: `utils/enumLabel.ts`, locale JSON | See "Enum labels" below. |

## Enum labels (last commit, approved by the operator on 2026-11-02)

Convention found in the bundles: `discovery_admin.<area>.<prefix>_<value>` looked up with `translateOrRaw(t, key, raw)` (`tasks.note_<n>`, `artifacts.kind_<kind>`, `documents.role_<role>`, `document.skip_reason_<r>`). Adding strings means editing **both** `apps/web/src/i18n/fallback/{en,de}.json` **and** `apps/api/scripts/seed_data/translations/{en,de}.json`, because `i18n/fallback/fallback.test.ts` ("matches the API seed") requires them to be equal, and a `discovery_admin.*` parity test requires en and de to match. Proposed keys: `discovery_admin.values.source_<govdata|pvog|fim|leika|manual>`, `task_status_<pending|claimed|completed|failed>`, `candidate_status_<staged|emitted>` (11 keys, 44 JSON lines). Task kinds and pipeline stages (`fetch_url`, `T0`) stay raw: they are identifiers shared with the CLI and runbooks. Call sites: `taskColumns` (source, status via `TaskStatusCell`), `catalogueColumns` (source), `candidateFilters` (status), `DiscoveryDocumentFilters` (source), `filterOptions.plainOptions` (becomes `enumOptions(t, prefix, values)` where labels apply).

This changes visible text, so existing assertions on raw values (for example the `taskColumns.test.tsx` expectation of `"fetch_url"`, `"pending"`, `"pvog"`) are updated deliberately, and the API seed must be re-run on deploy. The operator approved this on 2026-11-02, including the change to the API seed translations. Keep it as the last commit so the rest of the chapter stands alone if it is dropped.

## TDD loop

### Red

Characterisation first (pass on today's code, must pass after every step):

1. `relativeTime · formatRelativeTime` cases moved verbatim from `suggestions/utils/formatRelativeTime.test.ts` (minutes, hours, days ago, German "vor 5 Minuten") and `relativeTime · formatTimeUntil` cases moved from `formatRetryAfter.test.ts` (coarsest whole unit; null when unset, due or past). Written first against the old modules, then pointed at the new one.
2. `RequireAuth · guardOutcome` table (new, pure; the admin row is red today, everything else is characterisation): loading is `wait`, anonymous `login`, unconfigured `hidden`, moderator and admin pass `minRole: "moderator"` (the admin case fails today and is the red test), a user is `allow` for `"user"` and `forbidden` for `"moderator"`, an unknown role string is `wait`, an authenticated user without a role is `wait`.
3. `discoveryAdminGuardOutcome` table (new, pure; this function has no direct test today, only the integration test): loading `wait`, anonymous `login`, unconfigured `auth-unconfigured`, authenticated plus pending probe `wait`, plus ok `allow`, plus a 403 `ApiRequestError` `forbidden`, 401 `login`, 503 `disabled`, any other error `error` (the mapping in `discoveryAdminProbeErrors.ts:discoveryAdminProbeErrorOutcome`, which this table exercises; G1 then only adds its direct unit test if still missing).
4. `DocumentEmitPanel` (no test file today): `shows the preview when loaded`, `emitted candidate shows the emitted state and no loading or CLI hint` (happy); `error shows retry and calls onRetry` (negative).
5. Existing panel tests (`ArtifactsPanel.test.tsx`, `EmitPreviewPanel.test.tsx`, `DocumentEdgesPanel.test.tsx`) stay unchanged and green: they pin the "feedback inside the section shell" behaviour.
6. One pure-date pin: `formatTimeUntil · an unparseable date`. Today `new Date("garbage")` gives `NaN`, `NaN <= 0` is false and `pickUnit(NaN)` falls through to `["minute", 1]`, so the output is `"in 1 minute"`. Run it to record the real output. If it is wrong, fix it in its own red-green commit (return `null`), not inside the move.

New behaviour (fails because the code does not exist):

7. `QueryBoundary · renders children when the query is ready` (happy); `· shows an announced loading note and no children while loading` (`getByRole("status", { name: "Loading..." })`); `· shows retry instead of children on error and calls onRetry once`; `· a custom loading node replaces the default note` (negative paths). Loading is checked before error, as in the current panels.
8. `authGate · maps every AuthStatus` (exhaustive, so a new status fails to compile and fails the test).
9. `EMPTY_VALUE` sites: `mentionColumns · an empty condition and host render the placeholder`, `runGroups · lastRunGroup shows the placeholder for a run without finish time or stop reason` (the second is the visible `"-"` to `"—"` change).
10. `countRows · skips undefined entries` and `failureGroup · accepts a partial source map` (negative: `{ govdata: 2, pvog: undefined }` yields one row).
11. `queryKeys · suggestions.list keeps the key array shape` (equality against the literal array `["suggestions","list","pending",null,null,"en"]`), so the cache keys cannot drift.
12. Panels: `Panel · loading state is announced as a status` for `EmitPreviewPanel`, `DocumentEdgesPanel`, `DocumentEmitPanel` (fails today: bare text).

Run `npm test -- src/components/feedback src/utils src/features/auth src/features/discovery-admin src/features/suggestions src/i18n` and confirm 7-12 fail, 1-6 pass.

### Green

Order matters: each step is a separate commit and moves come before logic changes (`apps/web/CLAUDE.md`).

1. Moves first, one commit: the time formatters to `utils/relativeTime.ts` unchanged and `CompletenessChips` to `components/data-display`, repoint imports and tests, delete the old files. Then merge the two `pickUnit` copies.
2. Add `LoadingNote` and `QueryBoundary`; convert the four panels; delete `DiscoveryCatalogueQueryStatus.tsx`.
3. Add `authGate.ts`; convert both guards; replace the cast with `ROLES.findIndex`.
4. `EMPTY_VALUE`, `FilterOption`, `countRows`, `queryKeys.suggestions.list`.
5. Enum-label commit (approved 2026-11-02).

### Refactor

Judge by responsibility. Check that `QueryBoundary` stays "choose loading, error or content" (no empty-state logic: emptiness differs per panel, so it stays in the panels); that `ArtifactsPanel.panelState` has three arms left (rule of three holds); that `RequireAuth.guardOutcome` has one nesting level; that no wrapper was left that only forwards (`formatRetryAfter` must be gone, not re-exported). No `any`, no `as`, no `!` in touched files. Do not extract a helper for the two page-level loading texts: those containers belong to W4, which will use `LoadingNote`/`QueryBoundary`. Report `Refactor gate: smells found -> …, refactorings applied -> …` with before and after counts: panels with their own loading branch (4 to 0), duplicate `pickUnit` (2 to 1), `as` casts in touched files (3 to 0: `role as MinRole` plus the two `Record` casts), lines of `RequireAuth.tsx` and `discoveryAdminGuardOutcome.ts`.

## Verification

```bash
cd /home/schult_v/projects/redtape/apps/web
npx tsc --noEmit && npx eslint "src/**/*.{ts,tsx}"
npm test -- src/components/feedback src/utils src/features/auth src/features/discovery-admin src/features/suggestions src/features/candidates src/i18n src/architecture.test.ts
npm run format:check
# measures
grep -rn "DiscoveryCatalogueQueryStatus\|formatRetryAfter\|suggestions/utils/formatRelativeTime" src      # expect: no output
grep -rn 'role as MinRole\|as Record<string, number>' src                                                  # expect: no output
grep -rn 'common.loading' src/features/discovery-admin/components | grep -v 'role="status"\|aria-label'   # expect: no panel output
cd /home/schult_v/projects/redtape && ./ci.sh
```

If the enum-label commit lands, also run `cd /home/schult_v/projects/redtape/apps/api && uv run pytest tests -k translation` (find the exact test with `grep -rln seed_data/translations tests` first) because the API seed JSON changed.

## Parallel notes

- Runs beside **W1** (admin query plumbing). W1 edits `features/discovery-admin/{hooks,services}`, `services/api.ts`, `hooks/`, and the import lines of seven discovery-admin components (`DiscoveryTasksTable`, `DiscoveryTasksView`, `DiscoveryDocumentFilters`, `DiscoveryDocumentsTable`, `CatalogueSummaryChips`, `CatalogueServicesTable`, `CatalogueIndexPanel`). W2 edits `DiscoveryDocumentFilters.tsx` only if the enum-label commit lands (source options); that hunk is away from W1's import line. Do not touch any file under `features/discovery-admin/hooks` or `services`.
- Runs beside **B1** only through `apps/api/scripts/seed_data/translations/*.json` if the enum-label commit lands; B1 does not edit those files (it touches Python modules). Rebase, do not merge by hand.
- **W3** (boundary types) touches `suggestions/hooks/useSuggestionFilters.ts` and the documents hooks; W2 touches `suggestions/hooks/useSuggestionsListQuery.ts` and `app/queryKeys.ts`. Different files; if W3 also needs `queryKeys.ts`, it rebases on W2.
- **W4** follows (after W1 and W2): it replaces the page-level loading and error branches in `DiscoveryDocumentPage` and `DiscoveryPipelinePage` with `QueryBoundary`, and splits `taskColumns`. W2 leaves `containers/` and the structure of `taskColumns.tsx` alone and changes only its imports (and, optionally, enum labels).
- **T3** (architecture guards) allow-lists the violations this chapter removes: `CandidateScreenshot.tsx:5`, `candidateColumns.tsx:2`, `taskColumns.tsx:3` (shared relative time) and `CandidateReadinessCell.tsx:1` (`CompletenessChips`). W2's PR deletes those four baseline entries in `eslint.config.js` and `architecture.test.ts` **only if T3 has merged first**; otherwise T3 rebases and drops them. The new cross-feature import `discovery-admin` -> `auth/types/authGate` is inside T3's public surface (`<feature>/types/**`). Two T3 baseline rows stay unowned: `components/layout/menu/ProfileMenuRow.tsx:7` and `DocumentsMenuRow.tsx:5` (shared layout importing features); this chapter does not take them.
- Files this chapter must not touch: `architecture.test.ts` and `eslint.config.js` (T3; the only allowed edit is deleting the four baseline entries named above), `app/queryKeys.ts` beyond `suggestions.list`, `package.json`, lock files, anything under `apps/api` except the optional seed JSON.
- Core-doc inconsistency to report: the rollout lists `web/utils` as a touch, but `apps/web/src/utils` does not exist and `apps/web/CLAUDE.md` has no such layer; this chapter creates it and documents it in `CLAUDE.md`.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b refactor/shared-ui-blocks
```

```text
test(web): pin relative-time formatters, both auth guards and DocumentEmitPanel
refactor(web): move the time formatters and CompletenessChips to shared folders
refactor(web): add QueryBoundary and use it in the four admin panels
refactor(web): share the AuthStatus lookup between the two route guards
refactor(web): one empty-value placeholder, one FilterOption, no Record casts
feat(web): translate source and status values in the admin tables   (optional)
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.
