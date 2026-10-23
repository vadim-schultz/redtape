---
name: "Chapter 5 — Drain throughput and queue summary"
overview: "Make scheduled draining actually progress: multi-batch, time-bounded, daily, with a queue-summary route so the run report knows what remains."
todos:
  - id: summary
    content: "Add GET /machine/tasks/summary with ready, delayed, claimed, completed and failed counts for requested kinds"
    status: pending
  - id: remaining
    content: "Use the summary for remaining in the drain report and run finish"
    status: pending
  - id: schedule
    content: "Schedule discovery-drain.yml daily with bounds and a shared concurrency group; align platform-maintenance"
    status: pending
isProject: false
---

# Chapter 5 — Drain throughput and queue summary

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/crawlers-drain-throughput` · **Status:** planned

**Depends on:** [02](02-fetcher-hardening.md), [03](03-kind-filtered-claim.md), [04](04-retry-and-backoff.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

The scheduled discovery job runs every sixth day and drains one batch of 50 ([scheduled-jobs.md](../../../docs/operations/scheduled-jobs.md)). With 1,323 tasks pending that is months of backlog. Separately, the drain report always says `remaining: null, remaining_unknown: true` because no route exists to ask the queue ([discovery-operations decision D8](../../discovery-operations/gaps-and-decisions.md)).

## Contract

**Queue summary.** `GET /api/v1/discovery/machine/tasks/summary?kinds=...` (same default kinds as claim) returns counts: `pending_ready`, `pending_delayed` (future `not_before`), `claimed`, `claimed_stale` (lease expired), `completed`, `failed`. It reuses the repository layer behind `QueueMetricsRepository` and the "claimable" predicate from chapter 4. It never leases or mutates.

**Worker.** After the last batch, `run_worker_drain` asks for the summary and sets `remaining = pending_ready`, `remaining_unknown = false`. If the summary call fails the drain does **not** fail: `remaining` stays `null` with `remaining_unknown = true` and the stop reason is unchanged. `run_recorded_drain` already forwards `remaining_count` to the run finish route.

**Schedule.** `discovery-drain.yml` gains a daily `schedule` (04:00 UTC, after the 02:00 maintenance router) in addition to `workflow_dispatch`, with defaults `--max-tasks 50 --max-batches 20 --time-budget-seconds 1500`. Twenty batches of fifty is the ceiling; the one-second per-host interval and the time budget are the real bounds, which also keeps the load polite. A single `concurrency` group (`discovery-drain`, `cancel-in-progress: false`) is shared with the drain step of `platform-maintenance.yml` so two drains never overlap. The job `timeout-minutes` stays above the budget.

**The schedule ships switched off.** Scheduled runs require the repository variable `DISCOVERY_DRAIN_SCHEDULE` to equal `enabled` (`if: github.event_name == 'workflow_dispatch' || vars.DISCOVERY_DRAIN_SCHEDULE == 'enabled'`). Reason: until [chapter 15](15-snapshot-on-fetch.md) is live, a fast drain would consume the 1,323 pending fetch tasks as bare liveness probes and every page would need a second fetch later. The operator enables it in step S13 of [chapter 22](22-operator-manual-steps.md). The drain step inside `platform-maintenance.yml` keeps its current one-batch bound until then, so the six-day job's behaviour does not change in this chapter; chapter 15's live gate raises it to the same bounds.

The report is written to the job summary as JSON. A run with `succeeded: false` fails the job.

## TDD loops

### Loop A — Summary route

**Red** (`apps/api/tests/test_discovery_task_queue.py` or a new `test_discovery_queue_summary.py`)

1. `summary counts ready and delayed pending tasks separately` — one task with a future `not_before`.
2. `summary respects the kinds filter and defaults to legacy kinds`.
3. `summary requires the machine API key` — 401/403 without it.

**Green:** one grouped query with `FILTER` aggregates.

**Refactor:** share the claimable predicate with chapter 4; a single source of truth for "ready".

### Loop B — Remaining in the report

**Red** (`apps/discovery-ingest/tests/test_worker_drain.py`, `test_worker_run.py`)

1. `drain report carries remaining from the queue summary` — `remaining_unknown` false.
2. `drain report keeps remaining unknown when the summary fails` — run still `succeeded`.

**Green:** one extra client call at the end; no extra claim.

**Refactor:** keep report assembly in one function; the tally stays a dumb counter.

### Loop C — Workflow

No unit harness; verified live.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_task_queue.py
cd apps/discovery-ingest && python -m pytest tests/test_worker_drain.py tests/test_worker_run.py
gh pr checks --watch
gh workflow run discovery-drain.yml -f max_batches=3 -f time_budget_seconds=600
gh run watch && gh run view --log   # report shows batches=3 and a numeric remaining
```

Live gate: two consecutive dispatches show `remaining` decreasing. Overlap check: dispatch twice quickly; the second run waits on the concurrency group. The scheduled run is verified later, when the operator sets the variable (S13): confirm a manual-only repository does **not** start a scheduled run while the variable is unset, then record the first scheduled run ID after it is enabled.

## Out of scope

Changing the OpenPLZ/discovery calendar router, parallel workers, per-kind budgets, alerting.
