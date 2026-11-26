---
name: Chapter C1 - Flow aggregates
overview: "The flow response carries the coverage counters, the candidate and catalogue totals, and the budget fields that the removed admin views show."
id: C1
depends_on: []
touches:
  - apps/api/app/features/discovery/flow/
  - apps/api/app/features/discovery/admin_service.py
  - apps/api/app/schema/discovery/flow.py
  - apps/api/tests/test_discovery_flow_route.py
  - apps/api/tests/test_discovery_flow_aggregates.py
execution: chapter-implementer
isProject: false
---

# C1 - Flow aggregates

**Depends on:** none · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [01-rollout.md](../01-rollout.md)

## Goal

After C1, `GET /api/v1/discovery/admin/flow` returns the catalogue totals, the candidate totals, the source counts, the task totals, the LLM outcomes, the artifact totals against the storage cap, the fetch and stale counters, the failures by source, the last successful run, and the period and exhausted flag of each allotment. Each value equals the value that the coverage route returns for the same database.

## Read first

- [00-architecture.md](../00-architecture.md): the flow response contract, and invariants I1, I2 and I4. If this chapter and the architecture disagree, the architecture wins.
- [01-rollout.md](../01-rollout.md): the per-chapter gate.
- [gaps-and-decisions.md](../gaps-and-decisions.md): D4, D6 and D11. O3 sets the refresh cost check.

## Coordination scope

**Add:**

- `apps/api/app/features/discovery/flow/summary.py`: the reader that builds the summary fields from the coverage counts and the catalogue summary.
- `apps/api/tests/test_discovery_flow_aggregates.py`: the new tests of this chapter.

**Edit:**

- `apps/api/app/features/discovery/flow/service.py`: wires the summary into `FlowService.flow()`.
- `apps/api/app/features/discovery/flow/present.py`: the allotment mapping gains `period` and `exhausted`.
- `apps/api/app/features/discovery/admin_service.py`: `coverage()` calls the mapping functions that now live in `flow/summary.py`. Make no other change in this file.
- `apps/api/app/schema/discovery/flow.py`: the new response models.
- `apps/api/tests/test_discovery_flow_route.py`: change an assertion only where it compares a whole response.

**Do not edit:**

- `apps/api/app/features/discovery/repository/`: read only. If a repository method is missing, stop and report it.
- `apps/api/app/features/discovery/admin_controller.py`: C6 owns the removals. C1 adds no route and removes none.
- `apps/web/`: C4 owns the frontend.

## Work items

1. **Catalogue and candidate totals.**
   - **Red, happy path:** `test_flow_reports_catalogue_and_candidate_totals`. Seed two catalogue rows in two pipeline stages and one candidate in the `staged` status. The response has `catalogue.total == 2`, a `by_pipeline_stage` entry for each stage, `candidates.total == 1` and `candidates.staged == 1`.
   - **Red, negative path:** `test_flow_on_empty_database_reports_zero_totals`. An empty database returns `200`. Every total is zero, and `last_successful_run` is `null`. No error is raised.
   - **Green:** `summary.py` builds `catalogue` from `catalogue_summary()` and `candidates` from `fetch_coverage_metrics()`. `FlowService.flow()` includes both.
   - **Refactor candidates:** `FlowService.flow()` takes one `_summary(now)` helper. `service.py` stays under 100 lines.

2. **Coverage counters.**
   - **Red, happy path:** `test_flow_reports_coverage_counters_equal_to_coverage_route`. Seed one fixture. The flow fields `sources`, `tasks`, `llm_outcomes`, `artifacts`, `fetch_attempts_total`, `stale_claims`, `stale_runs`, `failures_by_source` and `last_successful_run` equal the values of `GET /api/v1/discovery/admin/coverage`. This parity test is removed with the coverage route in C6.
   - **Red, negative path:** `test_flow_summary_writes_nothing`. Count the rows of the task, run and catalogue tables. Call the flow route. The counts do not change (I4).
   - **Green:** `summary.py` maps the same `DiscoveryCoverageCounts` to the new fields. `admin_service.coverage()` imports the mapping functions from `summary.py`, so both routes share one mapping.
   - **Refactor candidates:** split the mapping into `task_totals`, `artifact_totals` and `last_run_read`, each under about five lines. `DiscoveryAdminService.coverage()` keeps one concern.

3. **Allotment period and exhausted flag.**
   - **Red, happy path:** `test_flow_allotments_report_period_and_exhausted`. Each allotment carries `period` as a string and `exhausted` as a boolean. Both equal the values of the budget snapshot.
   - **Red, negative path:** `test_flow_without_budget_rows_reports_no_allotments`. With no budget rows, `allotments` is an empty list, and the route answers `200`.
   - **Green:** `present.py` maps the two fields. `FlowAllotmentRead` in `schema/discovery/flow.py` gains them.
   - **Refactor candidates:** `allotment_read` keeps one concern. It maps fields and does nothing else.

4. **Existing contract.** `tests/test_discovery_flow_route.py` stays green (I2). Change its assertions only where they compare a whole response, and then add the new keys to the expected value.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Catalogue and candidate totals | `test_flow_reports_catalogue_and_candidate_totals` | `test_flow_on_empty_database_reports_zero_totals` |
| Coverage counters | `test_flow_reports_coverage_counters_equal_to_coverage_route` | `test_flow_summary_writes_nothing` |
| Allotment period and exhausted flag | `test_flow_allotments_report_period_and_exhausted` | `test_flow_without_budget_rows_reports_no_allotments` |

## Review gate

- Each new field has one happy-path test and one negative-path test. Each test was red before its green change.
- `tests/test_discovery_flow_route.py`, the machine API tests and the public candidate API tests pass.
- `summary.py` and `service.py` each stay under 100 lines.
- One mapping serves both the coverage route and the flow.
- The refactor report gives the query count and the elapsed time of one flow read against the test fixture (O3).

## Out of scope

- Per-stage task counts, the translation section and the recent failures. C3 owns them.
- Every frontend change. C4 owns them.
- Removing `coverage()` or any route. C6 owns the removals.

## Verification

```bash
# Run from the repository root. Postgres must answer on 127.0.0.1:5432, as ci.sh expects.
cd apps/api
PYTHONPATH=. DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape_pytest" REQUIRE_DB=1 \
  uv run pytest tests/test_discovery_flow_aggregates.py tests/test_discovery_flow_route.py -q
PYTHONPATH=. DATABASE_URL="sqlite:///test.db" uv run ruff check . && uv run ruff format --check . && uv run mypy app
```

Expected: `pytest` exits 0. `ruff check`, `ruff format --check` and `mypy` exit 0.

## Refactor report

_Pending. The implementer fills this in after the refactor pass. It must give the outcome of each refactor candidate and the query count and elapsed time of one flow read (O3)._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`.
- Create the chapter branch with `git checkout -b feat/discovery-admin-flow-c1-aggregates`.
- Commit the red tests first, as `test(discovery-flow): ...`. Then commit the green change, as `feat(discovery-flow): ...`. Then commit the refactor, as `refactor(discovery-flow): ...`.
- Run the local gate on the chapter branch with `./ci.sh all`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
