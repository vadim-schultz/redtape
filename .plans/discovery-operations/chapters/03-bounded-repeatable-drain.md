---
name: "Chapter 3 — Bounded repeatable worker drain"
overview: "Process multiple finite task batches or a finite time window while preserving leases, idempotency, and explicit run outcomes."
todos:
  - id: bounds
    content: "Define and validate batch-count and time-budget controls"
    status: pending
  - id: loop
    content: "Implement repeatable claim/process/report orchestration"
    status: pending
  - id: lifecycle
    content: "Connect drain outcomes to the persisted worker-run contract"
    status: pending
  - id: tests
    content: "Add paired multi-batch/no-progress tests and complete the refactor audit"
    status: pending
isProject: false
---

# Chapter 3 — Bounded repeatable worker drain

**Repo:** `redtape` (`apps/discovery-ingest`, machine API contract) · **Branch:** `feat/discovery-operations-bounded-drain` · **Status:** planned

**Depends on:** [02](02-queue-observability.md), [discovery-online lease reclaim](../../discovery-online/chapters/06-task-lease-reclaim.md), [discovery-online worker drain](../../discovery-online/chapters/07-ingest-worker-drain.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/discovery-operations`

## Goal

Turn the current one-batch command into a controlled drain that can make repeated progress without requiring repeated workflow dispatches and without introducing an infinite queue loop.

The command must remain safe for GitHub Actions and local smoke tests:

```text
start run
  → claim at most 50
  → process and settle that batch
  → stop on empty queue, batch limit, time budget, or infrastructure error
  → finish run with counts and stop reason
```

## Command contract

Preserve the existing command and its safe default:

```bash
python -m discovery_ingest worker drain --max-tasks 50
```

Add finite controls equivalent to:

- `--max-tasks`: tasks per claim request, 1–50, default 50;
- `--max-batches`: maximum number of claim/process batches, positive integer, default 1 for backward-compatible smoke behavior;
- `--time-budget-seconds`: optional positive wall-clock budget for the complete drain;
- an optional report path only if it does not replace the existing JSON stdout report.

When both bounds are supplied, the first reached bound wins. A command with no explicit new bound still processes exactly one batch. Zero, negative, non-numeric, or contradictory values fail before claiming work.

## Processing semantics

1. Start a persisted worker run through the machine API.
2. Claim pending tasks in existing priority, creation-time, and ID order.
3. Dispatch each task through the existing named handler:
   - `fetch_url` performs the current HTTP fetch, appends a fetch log, then completes or fails;
   - `enrich_metadata` fetches the FIM Steckbrief, posts the entity and claims, then completes or fails.
4. Finish each task before claiming the next batch. Do not claim ahead and leave a second batch leased while the first is being processed.
5. Stop when a claim response is empty, the maximum batch count is reached, or the time budget is exhausted.
6. Finish the run with the persisted report. A claim/API/orchestration failure marks the run failed; individual task failures remain counted and visible.

The report must distinguish:

- `batches`;
- `claimed`;
- `completed`;
- `failed`;
- `skipped`;
- `remaining`;
- `stop_reason`;
- `run_id`;
- whether the run was successful at orchestration level.

`remaining` must come from the queue-summary/run-finish contract defined by chapter 2. Never claim one extra task just to calculate remaining work. If the summary is unavailable, report `remaining: null` and an explicit `remaining_unknown` condition.

## Queue safety

Preserve all current queue guarantees:

- machine claim limit remains 1–50;
- lower priority values run first;
- claimed tasks have the existing 15-minute lease;
- expired leases are reclaimed at the next claim;
- task-level failures are reported and do not silently abort unrelated tasks;
- catalogue re-upsert does not multiply open or completed tasks;
- failed work is not retried inside the same run unless the existing API explicitly returns it to pending;
- FIM entity/claim writes remain idempotent.

The implementation must not add a boolean parameter that changes between “single batch” and “multi-batch” behavior throughout the worker. Select a named drain policy at the CLI boundary and pass a typed bound/policy object to the orchestrator.

## TDD loops

### Loop A — Multiple batches and empty-queue stop

**Red**

1. `worker drain processes two batches and aggregates the report` — assert both claim calls, task outcomes, run ID, and totals.
2. `worker drain stops after an empty claim response` — assert no third processing pass and `stop_reason=queue_empty`.

Run the focused worker suite and confirm both fail for the missing repeatable orchestration.

**Green**

Implement the smallest bounded loop around the existing claim/dispatch handlers. Keep task-kind dispatch in named handlers.

**Refactor**

Audit the containing drain method for nesting, branch count, duplicated count updates, and a single concern. Extract named policy, batch, and report units only where they add structure. Re-run the focused suite after each extraction.

### Loop B — Bound validation and no-progress safety

**Red**

1. `worker drain rejects non-positive batch or time bounds before claiming` — assert validation error and zero claim calls.
2. `worker drain stops at the configured bound and reports remaining work` — assert no overrun, a bounded stop reason, and no leaked speculative claim.

**Green**

Add typed CLI validation and stop checks. Preserve the one-batch default.

**Refactor**

Audit bound evaluation for monotonic time, duplicated stop predicates, and accidental retries. Keep termination decisions in one named policy and keep HTTP handling in the client.

### Loop C — Run lifecycle and failure reporting

**Red**

1. `worker drain finishes a successful bounded run with task failures counted` — assert orchestration success, failed task count, stop reason, and persisted report.
2. `worker drain marks the run failed when claim or run-finalization API fails` — assert non-zero command outcome and no false last-successful-run record.

**Green**

Connect the drain report to the run lifecycle from chapter 2, using `try/finally` only for the narrow finalization boundary and preserving the original API error.

**Refactor**

Audit run start/finalize error mapping, partial task outcomes, and report serialization. Ensure a failure in one task does not become a hidden run success, while expected per-task failures remain distinguishable from infrastructure failure.

## Verification

```bash
cd apps/discovery-ingest
python -m pytest tests/test_worker_drain.py tests/test_worker_run.py
cd ../..
./ci.sh
```

Manual verification must run a small local queue with more than one batch, then repeat the command after an interrupted claim to confirm lease reclaim. Production verification uses a bounded GitHub Actions dispatch and records the run report; it does not use direct database access.

## Out of scope

Crawler extraction, link following, robots policy, screenshots, evidence, automatic emit, scheduled promotion, and a standing worker process.
