---
name: "Chapter 4 — Queue hardening"
overview: "Dedup discovery tasks by artifact, lock the discovery claim so two claimers never overlap, persist why a task failed, and requeue only the transient failures after a cooldown."
todos:
  - id: dedup
    content: "Match an existing task on artifact_id when the target has one"
    status: pending
  - id: lock
    content: "Claim discovery tasks with FOR UPDATE SKIP LOCKED on the task rows"
    status: pending
  - id: failure-class
    content: "Persist failure_class and requeue transient failures after a 24 h cooldown"
    status: pending
  - id: llm-short-circuit
    content: "Complete an llm_extract with an unchanged cleaned-text hash at zero neurons"
    status: pending
isProject: false
---

# Chapter 4 — Queue hardening

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-queue-hardening` · **Status:** planned
**Depends on:** [2](02-observability-run-hygiene.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 2.4, waste 8) · **Decisions:** D15

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

Four queue defects keep work from reaching a stage or being repeated for nothing: a re-rendered page never gets a fresh extraction, two claimers can take the same task, a failed task never comes back, and an unchanged page is extracted again. Fix them in the API and the worker.

## Design

- **Dedup by artifact.** `find_task_for_target` (`apps/api/app/features/discovery/task_enqueue.py`, identity at `repository/tasks.py:57-68`) adds `artifact_id` to the match when the target has one. Existing `llm_extract` tasks already carry `artifact_id` (`llm_enqueue.py:40`), so a new snapshot of the same page gets a new task and an old one keeps its completed row. Tasks without an artifact keep the old identity.
- **Claim lock.** `list_pending_tasks_for_claim` (`repository/tasks.py:95-106`) selects with `FOR UPDATE SKIP LOCKED` on `DiscoveryTask`, so the outer join to the completeness subquery is not locked. The other three queues already do this (`leased_queue.py:67`).
- **Failure class.** A nullable `failure_class` (`String(32)`) on `discovery_task`, written in `settle_failure` (`task_retry.py`). The worker sends one of `transient`, `permanent`, `login_wall`, `robots`, `not_found`. Old rows stay null and count as permanent.
- **Requeue.** `POST /machine/tasks/requeue-transient` re-pends failed tasks with `failure_class = transient` whose last failure is at least 24 hours old. It resets `attempt_count`, takes `limit` from 1 to 200, and returns the count. Permanent failures are never touched.
- **Unchanged short circuit.** `LlmExtractHandler._pipeline` (`apps/discovery-ingest/discovery_ingest/worker/llm_extract.py`) compares the cleaned-text hash with the hash of the last completed extraction for the same catalogue service. If equal, it completes with `result_note = "unchanged"` and makes no model call. The raw artifact is not hashed, so nonces and timestamps do not defeat it.

## Files

**Edit**

- `apps/api/app/features/discovery/task_enqueue.py`
- `apps/api/app/features/discovery/repository/tasks.py`
- `apps/api/app/features/discovery/task_retry.py`
- `apps/api/app/features/discovery/machine_controller.py`
- `apps/api/app/schema/discovery/machine.py`
- `apps/discovery-ingest/discovery_ingest/worker/llm_extract.py`
- `apps/discovery-ingest/discovery_ingest/worker/settle.py` (the `client.tasks.fail` calls, lines 13 to 30, where the class is sent) and `apps/discovery-ingest/discovery_ingest/worker/lease_settle.py` (line 89)

**Create**

- one Alembic revision adding `discovery_task.failure_class`

**Do not edit**

- The completeness subquery (`completeness_subquery`) and the candidate listings. Discovery-throughput D6 keeps them unchanged.

## Red tests

| Test | Asserts |
| --- | --- |
| `the same artifact is deduped to one pending task` | Negative: a second enqueue with the same `artifact_id` returns the existing row. |
| `a new artifact for the same page gets a fresh task` | Happy: a different `artifact_id` creates a new row; the old completed row is untouched. |
| `two claimers never receive the same task` | Happy: two sessions claim at once; the union has no duplicates (test with two connections). |
| `a permanent failure is never requeued` | Negative: `failure_class = permanent` and `login_wall` rows are not returned by requeue. |
| `a transient failure is requeued only after the cooldown` | Happy: a failure 25 h old is requeued; one 2 h old is not. |
| `a requeued task starts with a fresh attempt count` | Happy: `attempt_count` is 0 after requeue. |
| `an unchanged cleaned-text hash completes without a model call` | Happy: zero neurons, `result_note = "unchanged"`. Negative: a changed hash calls the model. |

## Green

1. Write the dedup test first, then change `find_task_for_target`.
2. Add the claim lock test with two sessions, then the `with_for_update(skip_locked=True, of=DiscoveryTask)` clause.
3. Add the migration and the `failure_class` plumbing, then the requeue route and its schema.
4. Add the unchanged short circuit in `LlmExtractHandler`.

## Refactor gate

`find_task_for_target` takes at most one branch: artifact present or absent. The requeue route is one service method and one repository statement. Extract the cleaned-text hash comparison into its own function.

## Verification

```bash
cd apps/api && PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_discovery_task_queue.py tests/test_discovery_enqueue*.py && cd ../..
cd apps/discovery-ingest && .venv/bin/python -m pytest -q && cd ../..
./ci.sh
```

Live gate: after the merge, count requeue candidates in production with a read-only query and record the number in the run ledger before anyone calls the route.

## Commits

`test(api): define artifact-level dedup for discovery tasks`, `feat(api): dedup discovery tasks by artifact`, `test(api): define the discovery claim lock`, `feat(api): lock discovery claims with skip-locked`, `feat(api): persist and requeue transient task failures`, `feat(ingest): skip the model when a page's cleaned text is unchanged`.

## Out of scope

Refresh by epoch (chapter 11), change detection of fetched bodies (chapter 11), and any change to the completeness order.

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-queue-hardening
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
