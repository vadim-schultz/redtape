---
name: "Chapter 5 — Coverage and operational metrics tables"
overview: "Replace coverage badge clusters with grouped metric tables and reuse the summary composition across catalogue and coverage routes."
todos:
  - id: metric-model
    content: "Define stable row models and grouping for coverage, budgets, failures, and run metadata."
    status: pending
  - id: coverage-ui
    content: "Render grouped coverage tables inside the shared raised shell."
    status: pending
  - id: tests
    content: "Add populated, empty, and partial-failure coverage tests."
    status: pending
isProject: false
---

# Chapter 5 — Coverage and operational metrics tables

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-gui-harmonization-coverage` · **Status:** planned  
**Depends on:** [04-discovery-admin-tables.md](04-discovery-admin-tables.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-web-gui-harmonization` · **Release branch:** `main`

## Goal

Coverage becomes easy to scan and compare without decoding a field of badges. Source counts,
queue/status counts, task-kind counts, candidates, artifacts, LLM outcomes, failures, last-run
metadata, and budgets render in grouped tables using the shared shell and typography. Catalogue and
dedicated coverage routes reuse the same summary composition.

## Design decisions

- Prefer several small semantic tables over one wide table. Each table has a clear caption/title and
  a stable first column.
- A metric row contains a label, value, and optional context/status. Badges remain inside cells for
  severity or lifecycle state, never as the only representation of a metric.
- Coverage and budgets remain independent queries. A budget error is visible without erasing loaded
  coverage.
- Unknown source/kind keys remain renderable through a generic row model; known keys receive locale
  labels.
- Static summaries use DataTable presentation only when they benefit from column alignment; they do
  not advertise meaningless sort/filter controls.

## Files

**Add**

- coverage row-model utilities and grouped table components under
  `apps/web/src/features/discovery-admin/components/coverage/`
- tests for each grouped table and shared summary composition

**Edit**

- `CoverageChips.tsx`
- `LlmCoverage.tsx`
- `BudgetMeters.tsx` / `BudgetMeter.tsx`
- `FailuresBySource.tsx`
- `LastRunSummary.tsx`
- `DiscoveryCoveragePage.tsx`
- `DiscoveryCataloguePage.tsx`
- locale keys and fallback translations required by the new labels

**Do not edit**

- coverage API response shape unless chapter 3 proves a missing contract
- worker/budget calculation behavior
- discovery admin authorization

## Red tests

| Test | Asserts |
| --- | --- |
| `coverage renders source, queue, outcome, and artifact metrics as grouped rows` | Populated response values are visible in labelled tables with aligned values. |
| `catalogue and coverage reuse the same coverage summary composition` | The summary has one rendering contract across both routes. |
| `coverage renders unknown source and kind keys` | Negative: new server keys do not disappear or crash the view. |
| `coverage keeps metrics visible when budgets fail` | Negative: a budget error is explicit while coverage tables remain rendered. |
| `coverage renders an explicit empty state for no sources or failures` | Empty metric groups are understandable and not blank. |

Confirm the current badge-only expectations and new failure assertions before implementation.

## Green

1. Define pure row builders for each metric group.
2. Implement one grouped metric table and its tests.
3. Extract the shared summary composition.
4. Migrate remaining metric groups, preserving query independence and locale behavior.
5. Remove obsolete chip layout only after all grouped-table tests pass.

## Refactor gate

Audit `CoverageChips` and every new row builder/table as containing entities. Extract repeated
metric-row formatting and unknown-key handling. Replace chains with a keyed renderer/factory when
there are three or more metric variants. Keep transformation separate from rendering and rerun the
narrow coverage suite after each extraction.

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin/components/coverage src/features/discovery-admin/containers/DiscoveryCoveragePage.test.tsx src/features/discovery-admin/containers/DiscoveryCataloguePage.test.tsx
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Out of scope

- New coverage metrics
- Backend aggregation changes
- Public document/suggestion layout
- Pagination for static metric groups

## Git workflow

```bash
git checkout feat/plans-web-gui-harmonization && git pull
git checkout -b feat/web-gui-harmonization-coverage
```

Suggested commits:

```text
test(web): define grouped coverage metric states
feat(web): render discovery coverage as tables
```

Open the chapter PR into `feat/plans-web-gui-harmonization`.

