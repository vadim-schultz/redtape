---
name: "Chapter 4 — Retry and backoff"
overview: "Return transiently failed tasks to pending with exponential-style backoff up to a cap; keep permanent failures failed."
todos:
  - id: migration
    content: "Add attempt_count and not_before to discovery_task"
    status: pending
  - id: queue
    content: "Count attempts at claim, re-pend retryable failures with backoff, cap and fail"
    status: pending
  - id: claim-gate
    content: "Do not claim tasks whose not_before is in the future"
    status: pending
  - id: worker
    content: "Report retryable on fail from the fetch outcome"
    status: pending
isProject: false
---

# Chapter 4 — Retry and backoff

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`) · **Branch:** `feat/crawlers-retry-backoff` · **Status:** planned

**Depends on:** [03](03-kind-filtered-claim.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Two of the twelve production failures are transport errors (a connection reset and a timeout). Today every failure is final until a catalogue refetch, an open seam in [discovery-operations](../../discovery-operations/gaps-and-decisions.md). Transient failures should retry on their own; permanent ones (404, 403, robots denial) must not.

## Contract

**Migration.** `discovery_task.attempt_count int NOT NULL DEFAULT 0` and `not_before timestamptz NULL`. Downgrade drops both.

**Attempts.** `attempt_count` increments when a task is leased. A lease reclaimed after expiry has already counted its attempt.

**Fail route.** `TaskFailRequest` gains `retryable: bool = false`. In [`TaskQueue.fail`](../../../apps/api/app/features/discovery/task_queue.py):

- `retryable` and `attempt_count < MAX_ATTEMPTS` (3): status `pending`, `last_error` set, lease cleared, `not_before = now + BACKOFF[attempt_count - 1]` with `BACKOFF = (5 min, 30 min, 3 h)`.
- Otherwise: status `failed`, as today.
- A reclaimed expired lease whose attempts are exhausted becomes `failed` with `last_error = "lease expired after N attempts"` instead of cycling forever.

**Claim gate.** Pending tasks are claimable only when `not_before IS NULL OR not_before <= now`. Queue order is unchanged.

**Worker.** `DiscoveryMachineClient.fail_task(task_id, error=..., retryable=False)`. `fetch_url` and `enrich_metadata` pass `outcome.retryable` from [chapter 2](02-fetcher-hardening.md). Programming errors (unknown kind, unparseable steckbrief) are never retryable.

Every attempt still appends its own fetch log row, so the history of a retried task is visible.

## TDD loops

### Loop A — Re-pend and cap

**Red** (`apps/api/tests/test_discovery_task_queue.py`)

1. `retryable failure returns the task to pending with a backoff` — assert status, `not_before`, attempt count, `last_error`.
2. `permanent failure stays failed` — `retryable=false`.
3. `retryable failure at the attempt cap becomes failed` — third attempt.

**Green:** one `_settle_failure` method choosing the outcome; backoff in a named constant.

**Refactor:** keep `fail` under five lines by delegating to the settle method; no nested conditionals.

### Loop B — Claim gate and reclaim

**Red**

1. `claim skips a pending task whose not_before is in the future` and `claim takes it once not_before has passed` — inject `now`.
2. `reclaim of an expired lease at the cap marks the task failed` — and below the cap returns it to pending.

**Green:** extend the pending query and the reclaim statement.

**Refactor:** share the "claimable" predicate between claim and any queue-summary query (chapter 5).

### Loop C — Worker

**Red** (`apps/discovery-ingest/tests/test_worker_drain.py`)

1. `fetch_url reports a timeout as retryable` and `fetch_url reports a 404 as permanent` — assert the fail body.
2. `unknown kind is failed as non-retryable`.

**Green:** pass the flag through the existing failure path.

**Refactor:** one helper builds the fail call from an outcome; the three handlers share it.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_task_queue.py
cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd apps/discovery-ingest && python -m pytest tests/test_worker_drain.py tests/test_enrich_metadata_worker.py
gh pr checks --watch
```

Live gate: after the operator re-pends the two transport-failed tasks (chapter 22, S11), dispatch `discovery-drain.yml`. Each task either completes or shows `pending` with a future `not_before` in the admin Tasks API. Record the run ID and the observed state.

## Out of scope

Manual retry from the admin, per-host backoff, jitter, admin display of `attempt_count` (chapter 8).
