---
name: Chapter C4 - Flow page and probe
overview: "The flow page shows every figure of the flow response, and the admin menu probe calls the flow route."
id: C4
depends_on: [C1, C3]
touches:
  - apps/web/src/features/discovery-admin/components/FlowView/
  - apps/web/src/features/discovery-admin/containers/DiscoveryFlowPage.tsx
  - apps/web/src/features/discovery-admin/containers/DiscoveryFlowPage.test.tsx
  - apps/web/src/features/discovery-admin/types/flow.ts
  - apps/web/src/features/discovery-admin/utils/
  - apps/web/src/features/discovery-admin/hooks/useDiscoveryAdminProbe.ts
  - apps/web/src/features/discovery-admin/hooks/useDiscoveryAdminProbe.test.tsx
  - apps/web/src/features/discovery-admin/services/discoveryAdminApi.ts
  - apps/web/src/i18n/fallback/
execution: chapter-implementer
isProject: false
---

# C4 - Flow page and probe

**Depends on:** C1, C3 · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [01-rollout.md](../01-rollout.md)

## Goal

After C4, the flow page shows every figure of the flow response. The figures are the catalogue and candidate totals, the source counts, the task totals, the LLM outcomes, the artifacts against the storage cap, the fetch and stale counters, the failures by source, the last successful run, and the translation coverage per locale. The detail panel of a selected stage lists the stage's task counts and its recent failures. The discovery menu probe calls the flow route instead of the tasks route.

## Read first

- [00-architecture.md](../00-architecture.md): the flow response contract, and invariant I6.
- [gaps-and-decisions.md](../gaps-and-decisions.md): D3, D7 and D12.
- [01-rollout.md](../01-rollout.md): the per-chapter gate.

## Coordination scope

**Add:**

- `apps/web/src/features/discovery-admin/components/FlowView/FlowSummary.tsx`: the totals of the catalogue, the candidates, the sources, the tasks and the LLM outcomes.
- `apps/web/src/features/discovery-admin/components/FlowView/FlowArtifacts.tsx`: the artifact totals against the storage cap, and the last successful run.
- `apps/web/src/features/discovery-admin/components/FlowView/FlowTranslation.tsx`: the translation coverage per locale.
- `apps/web/src/features/discovery-admin/components/FlowView/FlowRecentFailures.tsx`: the recent failures of the selected stage.
- Test files beside each new component, one per component.

**Edit:**

- `apps/web/src/features/discovery-admin/components/FlowView/FlowView.tsx`: composes the new sections.
- `apps/web/src/features/discovery-admin/components/FlowView/FlowDetailPanel.tsx`: renders the stage's task counts and `FlowRecentFailures`.
- `apps/web/src/features/discovery-admin/components/FlowView/FlowStageCard.tsx`: shows the stage's task count, only when the stage has one.
- `apps/web/src/features/discovery-admin/types/flow.ts`: mirrors the contract of C1 and C3.
- `apps/web/src/features/discovery-admin/services/discoveryAdminApi.ts`: the probe calls `FLOW_PATH`. The function name `probeDiscoveryAdminAccess` stays.
- `apps/web/src/features/discovery-admin/hooks/useDiscoveryAdminProbe.test.tsx`: the probe tests.
- `apps/web/src/features/discovery-admin/containers/DiscoveryFlowPage.test.tsx`: the page tests.
- `apps/web/src/i18n/fallback/*.json`: new `discovery_admin.flow.*` keys. See the work items.

**Do not edit:**

- `apps/web/src/features/discovery-admin/components/coverage/`: read only. A component there may be reused when its props fit the flow data. Do not change those files. C5 decides what remains.
- The other admin views and their routes. C5 owns the removal.
- `apps/api/`: C1 and C3 own the backend contract.

## Work items

1. **Probe on the flow route.**
   - **Red, happy path:** `probes_the_flow_route_for_admin_access`. The probe requests a URL that ends with `/api/v1/discovery/admin/flow`. It sends no `limit` or `offset` query.
   - **Red, negative path:** `probe_403_hides_discovery_links`. A `403` from the flow route leaves the menu hidden. The existing test of the tasks route becomes this test.
   - **Green:** `probeDiscoveryAdminAccess` requests `FLOW_PATH`, and the comment above it names the flow route.
   - **Refactor candidates:** the constant `TASKS_PATH` and its comment go with the old probe. The file keeps only the probe and the flow calls.

2. **Totals section.**
   - **Red, happy path:** `FlowSummary` renders the catalogue total, the candidate total, the task total and the LLM outcome counts from a flow fixture with the C1 fields.
   - **Red, negative path:** `FlowArtifacts` shows the "no successful run" text when `last_successful_run` is `null`, and it shows no date.
   - **Green:** `FlowSummary` and `FlowArtifacts` read the fields. `FlowView` renders them below the allotment strip.
   - **Refactor candidates:** `FlowSummary` splits into small parts, for example one part for the counters and one for the sources. Each part stays under about five lines of render logic.

3. **Translation section.**
   - **Red, happy path:** `FlowTranslation` lists each locale with its translated count. The reused table of the coverage components may serve here, when its props fit the flow data.
   - **Red, negative path:** `FlowTranslation` shows the empty note when the denominator is zero, and it renders no table rows.
   - **Green:** `FlowTranslation` renders the section. `FlowView` adds it.
   - **Refactor candidates:** one component per section. `FlowView` stays a list of sections.

4. **Stage detail: task counts and recent failures.**
   - **Red, happy path:** `FlowDetailPanel` lists the recent failures of the selected stage, with the target URL, the attempt count and the result note of each.
   - **Red, negative path:** `FlowRecentFailures` shows the "no failures" note for a stage with an empty list, and it renders no list.
   - **Green:** `FlowRecentFailures` renders the list. `FlowDetailPanel` renders the task counts and the list.
   - **Refactor candidates:** `FlowDetailPanel` stays a composition of its parts. `SpendSection` keeps its own shape.

5. **Copy.** Each new text key goes into every `apps/web/src/i18n/fallback/*.json` file. English text fills the non-English files until a translation exists. The i18n parity test decides whether the files must match in key order and count.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Probe | `probes_the_flow_route_for_admin_access` | `probe_403_hides_discovery_links` |
| Totals | `FlowSummary` renders the totals | `FlowArtifacts` shows the no-run text for `null` |
| Translation | `FlowTranslation` lists each locale | `FlowTranslation` shows the empty note for zero |
| Recent failures | `FlowDetailPanel` lists the failures of the stage | `FlowRecentFailures` shows the no-failure note |

## Review gate

- Each test was red before its green change.
- `FlowView.tsx`, `FlowDetailPanel.tsx` and `FlowSummary.tsx` each compose their parts. None holds a branch for a section.
- Every figure of the flow response has a place on the page, or the review names the reason it has none.
- The probe reads only the flow route. A search for `discovery/admin/tasks` in `apps/web/src` finds nothing in the probe file.

## Out of scope

- Removing the old views and their files. C5 owns the removal.
- Filters, sorting and paging on the flow page.
- Row-level detail (O1).

## Verification

```bash
# Run from the repository root.
cd apps/web
npx vitest run src/features/discovery-admin/components/FlowView src/features/discovery-admin/containers/DiscoveryFlowPage.test.tsx src/features/discovery-admin/hooks/useDiscoveryAdminProbe.test.tsx src/i18n
npm run lint
npm run format:check
npm run typecheck
```

Expected: each command exits 0.

## Refactor report

_Pending. The implementer fills this in after the refactor pass. It must name each candidate and state its outcome._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`.
- Create the chapter branch with `git checkout -b feat/discovery-admin-flow-c4-flow-page`.
- Commit the red tests first, as `test(discovery-admin): ...`. Then commit the green change, as `feat(discovery-admin): ...`. Then commit the refactor, as `refactor(discovery-admin): ...`.
- Run the local gate on the chapter branch with `./ci.sh all`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
