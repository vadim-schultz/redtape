---
name: "Chapter 14 — Admin pipeline flow graph"
overview: "Draw the pipeline as a layered graph in the admin, with a state, a last run, the errors and the allowance for each stage, a strip of allotments at the top, and a text and list fallback for narrow screens."
todos:
  - id: flow-graph
    content: "Add a shared FlowGraph component with a pure layered layout and SVG edges"
    status: pending
  - id: flow-view
    content: "Build the discovery-admin FlowView with stage cards, the allotment strip and a detail panel"
    status: pending
  - id: route-and-menu
    content: "Add the /admin/discovery/flow route, its menu link and the query hook"
    status: pending
isProject: false
---

# Chapter 14 — Admin pipeline flow graph

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-flow-graph` · **Status:** planned
**Depends on:** [13](13-pipeline-flow-api.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3, item 6) · **Decisions:** D12

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

The operator should see the whole flow in one picture: which stage feeds which, what state each stage is in, when it last ran and what went wrong, and how much of each free allowance it spent. The picture must work without the mouse, on a phone, and in both colour modes.

## Design

- **Shared graph.** `apps/web/src/components/data-display/FlowGraph/` is generic, because features may not import each other's components (`architecture.test.ts`). It holds a pure layout (`layoutGraph.ts`: layers by longest path, barycentre ordering within a layer, a cycle is rejected with an error, output is deterministic), SVG edges that use the same arrowhead and the `border.emphasized` token as `FlowPaths`, and a render prop for node content. The candidate `FlowDiagram` is not changed (D12).
- **Feature view.** `apps/web/src/features/discovery-admin/components/FlowView/` (a `<X>View/` folder with an `index.ts` barrel) holds the stage card, the allotment strip, the callout for unused headroom, and the detail panel. Each file stays under about 100 lines.
- **Stage card.** The state is an icon and a text label, never colour alone. The card shows the ready count, failed in 24 h, the last run's age and its stop reason, and its main allotment as a meter. Selecting a card opens the detail panel with the recent runs, the failure classes and last error, the spend per resource, and the queue numbers (ready, delayed, claimed, completed in 24 h, oldest pending age).
- **Allotment strip.** One meter per resource with used and cap. A stacked bar shows which stage spent what. A callout names a resource with unused headroom while a stage that uses it has ready work.
- **Narrow screens.** Below the `md` breakpoint, the graph is replaced by a list in topological order, with the same stage content.
- **Data.** `useDiscoveryFlowQuery` wraps `useAdminQuery` with a key from `app/queryKeys.ts` and refetches every 60 s. The service call goes in `services/discoveryAdminApi.ts`; the response type goes in `types/flow.ts`.
- **Route and menu.** `/admin/discovery/flow` in `features/discovery-admin/routes`, and a link in `DiscoveryAdminMenuLinks.tsx` after Coverage, with an icon from `react-icons/fa`.
- **Strings.** `discovery_admin.flow.*` keys in English and German. Every state has a label and a one-line description.

## Files

**Create**

- `apps/web/src/components/data-display/FlowGraph/` (`FlowGraph.tsx`, `layoutGraph.ts`, `FlowEdges.tsx`, `index.ts`, and tests beside each)
- `apps/web/src/features/discovery-admin/components/FlowView/` (`FlowView.tsx`, `FlowStageCard.tsx`, `FlowAllotmentStrip.tsx`, `FlowDetailPanel.tsx`, `FlowList.tsx`, `index.ts`, tests)
- `apps/web/src/features/discovery-admin/containers/DiscoveryFlowPage.tsx` (and its test)
- `apps/web/src/features/discovery-admin/hooks/useDiscoveryFlowQuery.ts`
- `apps/web/src/features/discovery-admin/types/flow.ts`

**Edit**

- `apps/web/src/features/discovery-admin/routes.tsx`
- `apps/web/src/features/discovery-admin/components/DiscoveryAdminMenuLinks.tsx`
- `apps/web/src/features/discovery-admin/services/discoveryAdminApi.ts`
- `apps/web/src/app/queryKeys.ts`
- the locale message files that already hold `discovery_admin.*` keys

**Do not edit**

- `apps/web/src/features/candidates/components/FlowDiagram/` (D12).

## Red tests

| Test | Asserts |
| --- | --- |
| `the layout places a stage after every stage it feeds` | Happy: layers follow the edges. |
| `a cycle is rejected with an error` | Negative. |
| `the layout is deterministic for the same input` | Happy: two runs give the same coordinates. |
| `every state renders a text label, not only a colour` | Happy: each of the nine states. |
| `a stage with no run shows no run recorded` | Negative: no fabricated last run. |
| `the allotment callout names a resource with headroom and ready work` | Happy. |
| `no callout when the headroom is used` | Negative. |
| `below the breakpoint the list replaces the graph` | Happy: the list has the same stages in order. |
| `selecting a card opens its detail with the queue numbers` | Happy. |
| `the page refetches every 60 s` | Happy: a fake timer. |
| `the route and the menu link exist for admins only` | Negative: a non-admin does not see the link. |

## Green

1. Write the layout tests first, then `layoutGraph.ts`.
2. Write the `FlowGraph` render tests, then the component.
3. Write the state label tests, then `FlowStageCard`. Then the strip, the detail panel and the list.
4. Add the route, the menu link and the query hook last.

## Refactor gate

Each file stays under about 100 lines and each component under about three props. The state labels come from one map, not from a branch in each card. The layout function has no DOM access and no React import.

## Verification

```bash
cd apps/web && npm run test -- src/components/data-display/FlowGraph src/features/discovery-admin --run
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Live gate: open the page on staging as an admin, check the layout at 375 px and at 1440 px, in light and dark, and with the keyboard only. Record the screenshots in the run ledger.

## Commits

`test(web): define the layered layout for the flow graph`, `feat(web): add a layered FlowGraph component`, `test(web): define the flow stage states and the allotment strip`, `feat(web): show the pipeline flow on the discovery admin`, `feat(web): link the flow page from the discovery admin menu`.

## Out of scope

Changing the candidate `FlowDiagram`, editing any stage from the page, and the threshold tuning.

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-flow-graph
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
