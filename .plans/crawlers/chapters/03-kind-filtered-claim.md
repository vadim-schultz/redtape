---
name: "Chapter 3 — Kind-filtered claim and enum groundwork"
overview: "Let workers claim only the task kinds they handle, default to the two legacy kinds, add the new kind labels in one migration, and give workers an idempotent route to enqueue follow-up tasks."
todos:
  - id: migration
    content: "Add the three enum labels and discovery_task.input_key in one migration"
    status: pending
  - id: claim-filter
    content: "Add kinds to TaskClaimRequest with a safe default and filter in the repository"
    status: pending
  - id: enqueue-route
    content: "Add POST /machine/tasks, idempotent on (catalogue, kind, url, input_key)"
    status: pending
  - id: worker
    content: "Send kinds from the worker, add --kinds, add the enqueue client method"
    status: pending
isProject: false
---

# Chapter 3 — Kind-filtered claim and enum groundwork

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`) · **Branch:** `feat/crawlers-kind-filtered-claim` · **Status:** planned

**Depends on:** [01](01-ingest-ci.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

[`TaskQueue.claim_pending`](../../../apps/api/app/features/discovery/task_queue.py) and `list_pending_tasks_for_claim` in [repository/tasks.py](../../../apps/api/app/features/discovery/repository/tasks.py) lease any pending task regardless of kind. The current worker answers an unknown kind with `unsupported task kind` and fails the task. Adding new kinds without a filter would make the scheduled drain consume and fail them. This chapter adds the filter first and prepares every later chapter's schema in one place.

## Contract

**Migration** (new file under `apps/api/alembic/versions/`, latest head today is `20261023_discovery_run.py`):

- `ALTER TYPE discovery_task_kind ADD VALUE IF NOT EXISTS` for `harvest_payload`, `extract_page`, `capture_screenshot`, inside `op.get_context().autocommit_block()`.
- `discovery_task.input_key String(128) NULL`, no index yet.
- Downgrade drops `input_key`. Enum labels cannot be removed; the downgrade leaves them and the migration docstring says so. The model, `DiscoveryTaskKind` in [enums.py](../../../apps/api/app/models/discovery/enums.py), and `scripts/check_migrations.sh` (single head, upgrade, downgrade and upgrade, drift) must still pass.

**Claim route.** `TaskClaimRequest` gains `kinds: list[DiscoveryTaskKind] | None`. `None` means `LEGACY_TASK_KINDS = (fetch_url, enrich_metadata)`. An empty list is a 422. The filter lives in the repository query so priority and creation order are unchanged and the lease and reclaim behaviour is untouched.

**Task identity.** `TaskTarget` gains `input_key: str | None = None`. `find_task_for_target` compares it, so the same URL with a different `input_key` is a distinct task. Existing rows have `NULL` and behave as before.

**Enqueue route.** `POST /api/v1/discovery/machine/tasks` with `{catalogue_service_id, kind, target_url, priority?, input_key?}`:

- 404 if the catalogue row does not exist; 422 for an invalid kind or an over-long URL;
- reuses `enqueue_task_if_needed`, so an open or completed equivalent task is returned instead of duplicated;
- returns `{id, created}` with status 201 when created and 200 when it already existed;
- records the existing `task_enqueued` event.

**Worker.** `DiscoveryMachineClient.claim_tasks(limit, kinds)` sends `kinds`; `DiscoveryMachineClient.enqueue_task(...)` calls the new route. The ingest `DiscoveryTaskKind` literal widens. `worker drain` gains `--kinds` (comma separated, default the two legacy kinds); an unknown value fails before any claim. Dispatch still fails a claimed unknown kind as before, now as a non-retryable programming error.

## TDD loops

### Loop A — Claim filter

**Red** (extend `apps/api/tests/test_discovery_task_queue.py` and `test_discovery_machine_api.py`)

1. `claim without kinds ignores new task kinds` — seed a pending `extract_page` and a pending `fetch_url`; the claim returns only the latter.
2. `claim with kinds returns only those kinds in queue order` — priority then creation order preserved.
3. `claim with an empty or unknown kinds list is rejected` — 422, nothing leased.

**Green:** repository parameter plus schema default; no change to lease logic.

**Refactor:** keep the default in one named constant used by schema and queue; no duplicated tuples.

### Loop B — Enqueue route

**Red**

1. `enqueue creates a pending task and records an event` — 201, `created=true`.
2. `enqueue is idempotent for the same target and input key` — 200, same id, one row.
3. `enqueue distinguishes input keys` — same URL, two keys, two tasks.
4. `enqueue rejects an unknown catalogue row` — 404; `enqueue rejects an unknown kind` — 422.

**Green:** a thin controller method delegating to a queue method; reuse `enqueue_task_if_needed`.

**Refactor:** the queue method returns a small result type rather than a tuple.

### Loop C — Worker

**Red** (`apps/discovery-ingest/tests/test_worker_drain.py`)

1. `drain sends the configured kinds when claiming` — assert the request body.
2. `drain rejects an unknown kind before claiming` — zero claim calls.
3. `client enqueue_task posts the documented body` — mock transport assertion.

**Green:** thread `kinds` through `DrainPolicy`-adjacent configuration (a validated tuple), not a boolean flag.

**Refactor:** the CLI parses once and passes a typed value; no string splitting below the CLI.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_task_queue.py tests/test_discovery_machine_api.py
cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd apps/discovery-ingest && python -m pytest tests/test_worker_drain.py
gh pr checks --watch
gh workflow run discovery-drain.yml -f max_tasks=10 -f max_batches=1
gh workflow run discovery-drain.yml -f kinds=capture_screenshot -f max_batches=1   # must stop with queue_empty
```

Add a `kinds` input to `discovery-drain.yml` in this chapter. Live gate: the default dispatch behaves as before; the `capture_screenshot` dispatch claims nothing.

## Out of scope

Retry state (chapter 4), `artifact_id` (chapter 14), any handler for the new kinds, admin display of kinds (chapter 8).
