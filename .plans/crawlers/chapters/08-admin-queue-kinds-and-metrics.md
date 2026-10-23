---
name: "Chapter 8 — Admin queue kinds and metrics"
overview: "Show task kinds, attempts and delayed retries in the admin Tasks view, per-kind counts and candidate totals in Coverage."
todos:
  - id: api
    content: "Expose kind, attempt_count, not_before, input_key on tasks; add a kind filter; add per-kind and candidate counts to coverage"
    status: pending
  - id: web-types
    content: "Extend discovery-admin types and API functions"
    status: pending
  - id: web-ui
    content: "Kind filter, attempts and not-before columns, per-kind chips, candidate chips"
    status: pending
isProject: false
---

# Chapter 8 — Admin queue kinds and metrics

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/crawlers-admin-queue-kinds` · **Status:** planned

**Depends on:** [03](03-kind-filtered-claim.md), [04](04-retry-and-backoff.md), [07](07-pvog-payload-harvester.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Once five task kinds and retries exist, operators must be able to see which kind is stuck and which tasks are waiting for a retry. The existing Tasks and Coverage screens know only `fetch_url` and `enrich_metadata` ([types/index.ts](../../../apps/web/src/features/discovery-admin/types/index.ts) declares `DiscoveryTaskKind = "fetch_url" | "enrich_metadata"`).

## Contract

**API.**

- `DiscoveryTaskRead` gains `attempt_count`, `not_before` and `input_key`.
- `GET /api/v1/discovery/admin/tasks` accepts `kind` alongside `status` and `source`; an invalid value is 422.
- `GET /api/v1/discovery/admin/coverage` gains `task_counts_by_kind` (each kind with the five status counts) and `candidates` (`total`, `staged`, `emitted`, `mentions`).

**Web** (`apps/web/src/features/discovery-admin/`):

- widen `DiscoveryTaskKind`; extend the task type and the coverage type;
- `listDiscoveryTasks` accepts `kind`; `useDiscoveryTaskFilters` and `DiscoveryTaskFilters` gain a kind select;
- `DiscoveryTasksTable` shows attempts and a "retry after" cell when `not_before` is in the future;
- Coverage shows per-kind chips next to the existing queue chips, and candidate totals;
- strings in `apps/web/src/i18n/fallback/{de,en}.json` under `discovery_admin.*`; the architecture test (`apps/web/src/architecture.test.ts`) layering rules hold: containers own data hooks, components stay presentational.

## TDD loops

### Loop A — API

**Red** (`test_discovery_admin_api.py`, `test_discovery_coverage.py`)

1. `admin tasks lists kind attempts and not_before`.
2. `admin tasks filters by kind and rejects an invalid kind`.
3. `coverage returns per-kind status counts and candidate totals` — with and without rows.

**Green:** extend the DTOs and queries; reuse the grouped-count helper from queue metrics.

**Refactor:** no new query helper if an existing grouped query can take a second grouping column.

### Loop B — Web

**Red** (Vitest, beside the existing `DiscoveryTasksPage.test.tsx`, `DiscoveryCoveragePage.test.tsx`)

1. `tasks page sends the selected kind as a query parameter`.
2. `tasks table shows attempts and a retry-after cell only for delayed tasks`.
3. `coverage page renders per-kind chips and candidate totals`.
4. `tasks page tolerates an unknown future kind label` — renders the raw value instead of crashing.

**Green:** presentational components receive props; the container wires hooks.

**Refactor:** keep the filter state in the existing hook; no duplicated query-string logic.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_admin_api.py tests/test_discovery_coverage.py
cd apps/web && npm run test -- src/features/discovery-admin && npm run lint && npm run format:check && npm run typecheck && npm run build
gh pr checks --watch
```

Live gate: with the admin session, open Tasks, filter `harvest_payload`, and confirm the counts match the drain report from chapter 7; record a screenshot reference or the observed counts.

## Out of scope

Retry buttons, bulk actions, storage-bytes metrics (chapters 14 and 16), documents screens (chapters 10 and 20).
