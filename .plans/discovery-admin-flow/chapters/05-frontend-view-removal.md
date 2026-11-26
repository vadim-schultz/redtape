---
name: Chapter C5 - Frontend view removal
overview: "Only the flow page remains under the admin discovery routes, and the discovery menu shows one link to it."
id: C5
depends_on: [C4]
touches:
  - apps/web/src/features/discovery-admin/
  - apps/web/src/app/
  - apps/web/src/components/layout/
  - apps/web/src/test/adminRoutesApi.ts
  - apps/web/src/i18n/fallback/
execution: chapter-implementer
isProject: false
---

# C5 - Frontend view removal

**Depends on:** C4 · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [01-rollout.md](../01-rollout.md)

## Goal

After C5, the flow page is the only admin view under `/admin/discovery/*`. The route `/admin/discovery` redirects to `flow`. Every other admin route, such as `catalogue`, `coverage`, `tasks`, `documents`, `documents/:id` and `pipeline/:id`, shows the not-found view. The discovery menu shows one link, Flow. No module under `apps/web/src` imports a removed file.

## Read first

- [00-architecture.md](../00-architecture.md): the current admin surface, and invariants I1 and I6.
- [gaps-and-decisions.md](../gaps-and-decisions.md): D1, D2 and D12.
- [01-rollout.md](../01-rollout.md): the per-chapter gate.

## Coordination scope

**Add:**

- None.

**Edit:**

- `apps/web/src/features/discovery-admin/routes.tsx`: keeps the flow route and the index redirect to `flow`. Drops the other routes.
- `apps/web/src/features/discovery-admin/routes.test.tsx`: the route tests of this chapter.
- `apps/web/src/features/discovery-admin/components/DiscoveryAdminMenuLinks.tsx` and its test: one link, to `/admin/discovery/flow`, labelled "Flow" in English and "Ablauf" in German.
- `apps/web/src/features/discovery-admin/services/discoveryAdminApi.ts`: keeps the probe and the flow call only.
- `apps/web/src/features/discovery-admin/types/index.ts`: exports only what the kept files use.
- `apps/web/src/features/discovery-admin/adminStates.accessibility.test.tsx` and `adminSurfaces.integration.test.tsx`: keep only the cases of the flow page and the menu.
- `apps/web/src/app/routes.discoveryAdmin.test.tsx`: the mount tests for the flow route and the removed routes.
- `apps/web/src/components/layout/AppMenu.test.tsx` and `apps/web/src/components/layout/menu/DocumentsMenuRow.test.tsx`: update the discovery link assertions to one link.
- `apps/web/src/test/adminRoutesApi.ts`: removes the fixtures of the removed endpoints.
- `apps/web/src/i18n/fallback/*.json`: removes the `discovery_admin` keys that only removed views used.

**Delete:**

- Every other file under `apps/web/src/features/discovery-admin/`. The keep list is in the work items. Delete the rest.

**Do not edit:**

- `apps/web/src/app/routes.tsx`: the mount of `/admin/discovery/*` stays.
- `apps/web/src/components/layout/menu/DocumentsMenuRow.tsx`: the Browse documents link stays (D2).
- `apps/web/src/components/layout/menu/LanguageMenuRow.tsx`: C2 owns it.
- `apps/api/`: C6 owns the backend removal.

## Work items

1. **Route and menu.**
   - **Red, happy path:** `shows_one_link_to_the_flow_route`. With a successful probe, the menu shows one discovery link, to `/admin/discovery/flow`.
   - **Red, negative path:** `renders_not_found_for_removed_admin_routes`. Each removed path renders the not-found view: `catalogue`, `coverage`, `tasks`, `documents`, `documents/abc` and `pipeline/abc`. The index test changes from `catalogue` to `flow`.
   - **Green:** `routes.tsx` drops the removed routes. The index redirect targets `flow`. `DiscoveryAdminMenuLinks.tsx` keeps one entry in its list.
   - **Refactor candidates:** the list with one entry gives way to one `MenuIconLink`, if the list reads better that way. The `MENU_VIEWS` map already dispatches the three view states (links, unavailable and hidden). The map has three arms, which the rule of three allows as a dispatch table. State that outcome in the report.

2. **Remove the views.** The red step of item 1 covers this removal, because the removed routes fail until the files are gone. The green step deletes the files.
   - **Keep, after C4:** the whole `components/FlowView/` folder. `components/DiscoveryAdminLayout.tsx`, `DiscoveryAdminLoading.tsx`, `DiscoveryAdminMenuLinks.tsx`, `DiscoveryAdminMenuUnavailable.tsx`, `RequireDiscoveryAdmin.tsx`, and their tests. Each `components/coverage/` file that C4 imports. `containers/DiscoveryFlowPage.tsx` and its test. `hooks/useAdminQuery.ts`, `hooks/useDiscoveryFlowQuery.ts` and `hooks/useDiscoveryAdminProbe.ts`, with their tests. `types/flow.ts` and `types/values.ts`. `utils/flowLabels.ts`, `utils/flowModel.ts`, `utils/flowStates.ts`, `utils/discoveryAdminProbeErrors.ts` and `utils/discoveryAdminGuardOutcome.ts`, with their tests. `constants/queryTiming.ts` if a kept file imports it.
   - **Delete:** every other file under the feature folder. That covers the catalogue, coverage, tasks, documents, pipeline and candidate containers, the artifact, budget, candidate, catalogue and task components and hooks, the list query services, and the candidate and catalogue types. `apps/web/src/features/discovery-admin/containers/sectionPrefetch.ts` goes too.
   - **Verify the keep list by import graph.** Run `npm run typecheck`. Any kept file that imports a deleted file fails the check. Repair the import in the kept file. Do not restore a removed view.
   - **Refactor candidates:** remove the `discovery_admin` i18n keys that no kept file reads. Check each key with `grep` before its removal.

3. **Trim the mixed test files.** Each shared test file keeps the cases of the flow page, the menu and the guard. The cases of the removed views go.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Menu | `shows_one_link_to_the_flow_route` | `renders_not_found_for_removed_admin_routes` |
| Index redirect | `/admin/discovery` redirects to `flow` | `renders_not_found_for_removed_admin_routes` |
| File removal | The keep list builds and tests pass | `npm run typecheck` fails on any import of a deleted file |

## Review gate

- Each route test was red before the route change.
- The keep list matches the files that remain. No other file remains under the feature folder.
- `DocumentsMenuRow.tsx` is unchanged, and the Browse documents link still works.
- The discovery menu shows one link to `/admin/discovery/flow`.
- The refactor report states the outcome of the `MENU_VIEWS` check and of the i18n key removal.

## Out of scope

- The backend endpoints. C6 owns them.
- The public documents pages under `apps/web/src/features/documents` or elsewhere. They are not admin views.
- The translation coverage component, unless C4 reused it. If C4 reused it, it stays.

## Verification

```bash
# Run from the repository root.
cd apps/web
npx vitest run src/features/discovery-admin src/app src/components/layout src/i18n
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
grep -rn "features/discovery-admin/containers/Discovery\(Catalogue\|Coverage\|Tasks\|Documents\|Document\|Pipeline\)Page" apps/web/src || echo "no matches"
```

Expected: each `npm` command exits 0. The `grep` prints no match, and the script prints `no matches`.

## Refactor report

_Pending. The implementer fills this in after the refactor pass. It must give the keep list as built, the outcome of the `MENU_VIEWS` check and the i18n keys removed._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`.
- Create the chapter branch with `git checkout -b feat/discovery-admin-flow-c5-frontend-removal`.
- Commit the red route tests first, as `test(discovery-admin): ...`. Then commit the removal, as `refactor(discovery-admin): remove admin views except flow`.
- Run the local gate on the chapter branch with `./ci.sh all`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
