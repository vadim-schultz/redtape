---
name: "Chapter 2 — Queue observability"
overview: "Expose durable queue, fetch, lease, source-failure, and worker-run metrics so operators can distinguish backlog from worker health."
todos:
  - id: run-contract
    content: "Define persisted worker-run lifecycle and machine API contract"
    status: pending
  - id: metrics
    content: "Add repository and response metrics for queue, fetch, lease, and source failures"
    status: pending
  - id: admin
    content: "Render the expanded metrics in the discovery admin coverage surface"
    status: pending
  - id: tests
    content: "Add paired API, repository, and UI tests and complete the refactor audit"
    status: pending
isProject: false
---

# Chapter 2 — Queue observability

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`, `apps/web`) · **Branch:** `feat/discovery-operations-queue-observability` · **Status:** planned

**Depends on:** [01](01-representative-row-smoke.md) · [discovery-layer coverage](../../discovery-layer/chapters/19-coverage-metrics.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/discovery-operations`

## Goal

Make the queue operationally legible. The current coverage response exposes source counts, pending tasks, failed tasks, and T4 rows, but it cannot answer how much work exists, how many attempts have happened, whether claimed work is stale, which sources fail, or whether the last worker run actually completed.

## Design decisions

### Persist run health explicitly

Do not infer “last successful run” from `discovery_fetch_log.fetched_at`: a fetch timestamp cannot distinguish a successful drain from a worker crash, a partial batch, or an old run.

Add a minimal operational `discovery_run` aggregate, or an equivalent append-only machine-API run event if implementation proves that no table is needed. The implementation must settle this choice before coding. The preferred record contains:

- `id`;
- `kind`, initially `worker_drain`;
- `status`, with `running`, `succeeded`, and `failed`;
- `started_at` and `finished_at`;
- `claimed_count`, `completed_count`, `failed_count`, and `skipped_count`;
- `remaining_count`, when the queue-summary contract can calculate it safely;
- `stop_reason`, such as `queue_empty`, `batch_limit`, `time_budget`, or `error`;
- bounded error detail.

“Succeeded” means the drain orchestration completed its bounded run without an infrastructure/API failure. Individual task failures remain visible in the report and source metrics; they do not disappear behind a successful run status.

Workers create and finish the run through machine routes. An interrupted `running` record is not selected as the last successful run. A stale running record must be visible or classifiable from its age.

### Metric contract

Extend the admin coverage response with typed fields equivalent to:

```text
task_counts:
  total
  pending
  claimed
  completed
  failed
fetch_attempts_total
stale_claims
failures_by_source
last_successful_run
```

Definitions:

- **total** counts all persisted tasks, including completed and failed history;
- **pending**, **claimed**, **completed**, and **failed** group current task status;
- **fetch attempts** counts append-only `discovery_fetch_log` rows;
- **stale claims** counts `claimed` tasks whose `lease_expires_at` is before the current time;
- **failures by source** joins failed tasks to `catalogue_service.source`;
- **last successful run** is the latest explicitly persisted successful bounded drain, or `null` when none exists.

Do not call these values “percentage coverage” unless an authoritative expected source universe exists. They are operational counts.

### API and UI boundaries

Keep machine run lifecycle routes separate from the allowlisted admin read model. The worker must be able to start and finish a run with `X-API-Key`; the admin UI reads the aggregate through the existing bearer/JWT guard. Do not give the worker an admin JWT or make the web client responsible for run state.

The existing `/admin/discovery/coverage` page should show:

- queue status counts;
- fetch attempts;
- stale leases;
- failed tasks grouped by source;
- the last successful run timestamp and report summary;
- explicit empty and unavailable states.

The existing task filters and pipeline detail remain the drill-down for individual rows.

## TDD loops

### Loop A — Aggregate queue metrics

**Red**

1. `coverage returns total and status counts for mixed task history` — assert total, pending, claimed, completed, and failed counts.
2. `coverage reports stale leases and per-source failures` — assert an expired claimed task and failed tasks grouped by catalogue source; assert an unexpired lease is not stale.

Run the focused API tests and confirm both fail for the missing metric contract.

**Green**

Implement repository aggregation and typed response mapping. Keep SQL aggregation in the repository and keep controller methods orchestration-only.

**Refactor**

Audit the containing repository/service/response path for duplicated status predicates, time-zone mistakes, source-join duplication, and untyped metric dictionaries. Re-run the focused suite after each extraction.

### Loop B — Run lifecycle

**Red**

1. `worker run lifecycle records a successful bounded run` — assert start, finish, counts, stop reason, and selection as the latest successful run.
2. `failed or interrupted run is not reported as last successful` — assert an API failure or unfinished run remains observable and does not replace a previous successful run.

**Green**

Add the smallest machine API and persistence contract that records lifecycle and report data without direct worker database access.

**Refactor**

Audit run creation, completion, stale detection, and latest-success selection for one concern per unit, explicit error mapping, and no boolean mode parameter. Re-run the focused suite after each extraction.

### Loop C — Admin presentation

**Red**

1. `CoverageChips renders queue and run metrics` — assert the new counts and last-successful-run state.
2. `Coverage page shows explicit unavailable or empty state` — assert missing/failed metrics do not render misleading zero-success language.

**Green**

Extend the existing coverage query/types/components without creating a second discovery API client or a second access guard.

**Refactor**

Audit the coverage container, metric components, locale keys, and status rendering. Keep query orchestration in the container and presentation in named components.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_coverage.py tests/test_discovery_run.py
cd ../discovery-ingest
python -m pytest tests/test_worker_drain.py tests/test_worker_run.py
cd ../web
npm run test -- src/features/discovery-admin
cd ../..
./ci.sh
```

The exact new test filenames may be chosen during implementation, but the paired behaviors and negative paths above are mandatory.

## Out of scope

Crawler extraction, screenshots, evidence, automatic retries independent of catalogue refetch, scheduled emit, voting, moderation, and canonical promotion.
