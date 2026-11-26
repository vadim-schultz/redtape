---
name: Chapter C3 - Flow translation and failures
overview: "The flow response carries the translation coverage per locale, the task counts of each stage, and at most 20 recent failed tasks per stage."
id: C3
depends_on: [C1]
touches:
  - apps/api/app/features/discovery/flow/
  - apps/api/app/schema/discovery/flow.py
  - apps/api/tests/test_discovery_flow_translation.py
  - apps/api/tests/test_discovery_flow_failures.py
execution: chapter-implementer
isProject: false
---

# C3 - Flow translation and failures

**Depends on:** C1 · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [01-rollout.md](../01-rollout.md)

## Goal

After C3, the flow response carries three new things. The `translation` section holds the same per-locale counts as `GET /api/v1/admin/translations/coverage`. Each stage carries `tasks`, its task counts by status, or `null` for a queue stage. Each stage also carries `recent_failures`, the newest failed tasks of the stage, at most 20 of them.

## Read first

- [00-architecture.md](../00-architecture.md): the flow response contract, and invariants I1, I2 and I4.
- [gaps-and-decisions.md](../gaps-and-decisions.md): D5, D7 and D11. O1 sets the row-level limit. Its default applies here. If the user changes O1 before this chapter starts, stop and report.
- [01-rollout.md](../01-rollout.md): the per-chapter gate.

## Coordination scope

**Add:**

- `apps/api/app/features/discovery/flow/translation.py`: builds the `translation` section from the translation feature's coverage read.
- `apps/api/app/features/discovery/flow/task_reads.py`: one grouped query for the task counts by kind and status.
- `apps/api/app/features/discovery/flow/failure_reads.py`: one query for the recent failed tasks of one stage.
- `apps/api/tests/test_discovery_flow_translation.py`: the translation tests.
- `apps/api/tests/test_discovery_flow_failures.py`: the task count and failure tests.

**Edit:**

- `apps/api/app/features/discovery/flow/service.py`: wires the three readers into `FlowService.flow()`.
- `apps/api/app/features/discovery/flow/stage.py` and `apps/api/app/features/discovery/flow/present.py`: the stage mapping gains `tasks` and `recent_failures`.
- `apps/api/app/schema/discovery/flow.py`: the new response models.

**Do not edit:**

- `apps/api/app/features/translation/`. Call `TranslationAdminService.coverage()` from the flow package, and change nothing in that feature. C6 moves the builder out of that service, so this chapter must not change it.
- `apps/api/app/features/discovery/admin_controller.py` and the other admin controllers. C6 owns the removals.
- `apps/api/app/features/discovery/repository/`: read only. Add a query to a new reader module instead.
- `apps/web/`: C4 owns the frontend.

## Work items

1. **Translation section.**
   - **Red, happy path:** `test_flow_reports_translation_coverage_per_locale`. Use the seed of the existing translation coverage test. The flow `translation.locales` equals the `locales` of `GET /api/v1/admin/translations/coverage`, and the two denominators are equal.
   - **Red, negative path:** `test_flow_translation_section_is_empty_without_german_cards`. With no German card, both denominators are zero, each locale has zero counts, and the route answers `200`.
   - **Green:** `translation.py` returns `FlowTranslationRead`, built from the translation coverage read. `FlowResponse.translation` is set in `service.py`.
   - **Refactor candidates:** `service.py` calls one reader per section, and each reader keeps one concern. `translation.py` maps only.

2. **Stage task counts.**
   - **Red, happy path:** `test_flow_stage_reports_task_counts_of_its_kinds`. A stage with tasks in each of the four statuses reports them as `pending`, `claimed`, `completed` and `failed`. Tasks of another stage do not count.
   - **Red, negative path:** `test_flow_queue_stage_reports_null_task_counts`. An embedding or translation queue stage has `tasks: null`.
   - **Green:** `task_reads.py` runs one grouped query over `group_by(kind, status)`. `present.py` maps the counts of each stage's kinds.
   - **Refactor candidates:** the query runs once per request, not once per stage. A small helper sums the counts of the kinds of a stage.

3. **Recent failures.**
   - **Red, happy path:** `test_flow_recent_failures_list_newest_failed_tasks_first`. A stage with 25 failed tasks returns 20 entries, newest first. Each entry holds `id`, `kind`, `source`, `target_url`, `attempt_count`, `result_note` and `updated_at`.
   - **Red, negative path:** `test_flow_recent_failures_exclude_completed_and_pending_tasks`. A stage with only completed and pending tasks returns `recent_failures: []`, not `null`.
   - **Green:** `failure_reads.py` runs one query per stage. It filters on `status == failed`, orders by `updated_at` descending and limits to 20.
   - **Refactor candidates:** `failure_reads.py` holds one function, and `service.py` calls it through one helper. The stage count of the route is fixed, so the number of queries stays fixed too. State that count in the refactor report.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Translation section | `test_flow_reports_translation_coverage_per_locale` | `test_flow_translation_section_is_empty_without_german_cards` |
| Stage task counts | `test_flow_stage_reports_task_counts_of_its_kinds` | `test_flow_queue_stage_reports_null_task_counts` |
| Recent failures | `test_flow_recent_failures_list_newest_failed_tasks_first` | `test_flow_recent_failures_exclude_completed_and_pending_tasks` |

## Review gate

- Each test was red before its green change.
- The translation section equals the translation coverage route for the same seed.
- `flow/service.py` stays under 100 lines. Each reader lives in its own module.
- The refactor report gives the number of queries that one flow read runs.
- No file in `apps/api/app/features/translation/` changed.

## Out of scope

- Removing the translation route or its service. C6 owns that removal.
- Row-level task lists beyond the 20 recent failures (O1).
- The frontend. C4 shows these fields.

## Verification

```bash
# Run from the repository root. Postgres must answer on 127.0.0.1:5432, as ci.sh expects.
cd apps/api
PYTHONPATH=. DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape_pytest" REQUIRE_DB=1 \
  uv run pytest tests/test_discovery_flow_translation.py tests/test_discovery_flow_failures.py \
  tests/test_discovery_flow_route.py tests/test_translation_admin_api.py -q
PYTHONPATH=. DATABASE_URL="sqlite:///test.db" uv run ruff check . && uv run ruff format --check . && uv run mypy app
```

Expected: `pytest` exits 0. `ruff check`, `ruff format --check` and `mypy` exit 0. `test_translation_admin_api.py` passes unchanged, which shows that the translation route still answers.

## Refactor report

_Pending. The implementer fills this in after the refactor pass. It must give the query count of one flow read and the outcome of each refactor candidate._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`.
- Create the chapter branch with `git checkout -b feat/discovery-admin-flow-c3-translation-failures`.
- Commit the red tests first, as `test(discovery-flow): ...`. Then commit the green change, as `feat(discovery-flow): ...`. Then commit the refactor, as `refactor(discovery-flow): ...`.
- Run the local gate on the chapter branch with `./ci.sh all`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
