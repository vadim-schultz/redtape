---
name: "Chapter 13 — Pipeline flow API"
overview: "Add the static topology of the pipeline, a pure function that gives each stage a state, and an admin route that returns the stages, their edges, their last runs and the allowance each one spends."
todos:
  - id: topology
    content: "Define stages, edges, resources and cadence in one topology module"
    status: pending
  - id: states
    content: "Classify each stage into one state with a pure function and a threshold table"
    status: pending
  - id: route
    content: "Serve the flow to admins at /api/v1/discovery/admin/flow"
    status: pending
isProject: false
---

# Chapter 13 — Pipeline flow API

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-flow-api` · **Status:** planned
**Depends on:** [2](02-observability-run-hygiene.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3, item 6) · **Gaps:** flow-graph thresholds (gaps-and-decisions, open seams)

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

The admin needs one response that describes the whole flow: every stage, how each one feeds the next, its state and last run, and the allowance it draws on. The state logic must be a pure function that can be tested without a database, and the topology must cover every task and run kind, so a new kind cannot be silently left out.

## Design

- **Topology.** `apps/api/app/features/discovery/flow/topology.py` lists the stages as data: `id`, `label`, the task kinds or queue it reads, the run kind or `stage` it writes (chapter 2), the allotment it draws on, its cadence in hours, and the edges it feeds. The stages are seed, render, extract (LLM), capture, embed, card translation, page translation, and the three pipeline phases (chapter 12) as groups.
- **Coverage check.** A test asserts that every `DiscoveryTaskKind` and every run stage appears in the topology, so a new kind fails the build.
- **State rules.** `flow/state.py` has one function, `classify_stage(stage, facts, thresholds) -> StageState`, with the states `dead`, `budget_stopped`, `throttled`, `blocked`, `starved`, `overdue`, `backlogged`, `flowing` and `idle`. `facts` holds the ready count, the 24 h counts, the last run's stop reason and age, and the allotment headroom. The rules run in that order, and the first match wins.
- **Thresholds.** One table in `flow/thresholds.py`: overdue at 1.5 times the cadence, backlogged at twice the cadence, headroom counted as unused above 20% of the cap. These are first guesses and are tuned after a week (gaps).
- **Route.** `GET /api/v1/discovery/admin/flow` in `admin_controller.py`, behind the existing admin guard. The response holds `stages[]` (id, label, state, ready, failed_24h, last_run), `edges[]` (from, to, tasks_created_24h, manual_only), `allotments[]` (resource, used, cap, spent_by_stage) and `unused_headroom[]` (resource, stage with ready work).
- **Spend.** `spent_by_stage` sums the `spend` field of runs from the last 24 hours (chapter 2), grouped by stage.
- **Service.** A `FlowService` composes the repositories' summaries; the controller stays a single call.

## Files

**Create**

- `apps/api/app/features/discovery/flow/__init__.py`
- `apps/api/app/features/discovery/flow/topology.py`
- `apps/api/app/features/discovery/flow/state.py`
- `apps/api/app/features/discovery/flow/thresholds.py`
- `apps/api/app/features/discovery/flow/service.py`
- `apps/api/app/schema/discovery/flow.py`
- `apps/api/tests/test_discovery_flow_state.py`, `test_discovery_flow_topology.py`, `test_discovery_flow_route.py`

**Edit**

- `apps/api/app/features/discovery/admin_controller.py`
- `apps/api/app/features/discovery/dependencies.py` (provide `FlowService`)
- `apps/api/tests/` (the OpenAPI snapshot)

**Do not edit**

- The existing coverage route and its response. The flow is a new route.

## Red tests

| Test | Asserts |
| --- | --- |
| `a stage with no producer is dead` | Happy: `dead`. |
| `a stage stopped on a budget with ready work is budget_stopped` | Happy. |
| `ready work with headroom and a clock stop is throttled` | Happy: the free tier is left on the table. |
| `ready work with the allotment full is not throttled` | Negative: a full allotment is `budget_stopped`, not `throttled`. |
| `nothing ready and the upstream is overdue is blocked` | Happy. |
| `nothing ready and the last run was queue_empty is starved` | Happy. |
| `a run older than 1.5 times the cadence is overdue` | Boundary: exactly 1.5 times is not overdue. |
| `every task kind and run stage appears in the topology` | Coverage: a missing kind fails. |
| `the route is admin-only` | Negative: a non-admin gets 403. |

## Green

1. Write the topology coverage test first, then the topology data.
2. Write the state tests one at a time, in the rule order, then the function.
3. Add the service, the schema and the route; update the OpenAPI snapshot in the same commit.

## Refactor gate

`classify_stage` is one list of `(predicate, state)` pairs, not a chain of branches. Each predicate is a named function of the facts. The topology is data only.

## Verification

```bash
cd apps/api && PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_discovery_flow_*.py && cd ../..
./ci.sh
```

Gate: every state has a happy and a negative test, and the coverage test passes. After the merge, call the route on production with an admin key and record the states in the run ledger.

## Commits

`test(api): define the pipeline topology coverage`, `feat(api): describe the pipeline stages and edges`, `test(api): define each stage state`, `feat(api): classify pipeline stage states`, `feat(api): serve the pipeline flow to admins`.

## Out of scope

The admin page (chapter 14), changing any stage's behaviour, and the thresholds' tuning, which waits for a week of data.

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-flow-api
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
