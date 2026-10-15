---
name: "Chapter 5 — Crawler targets table"
overview: "Admin tasks page listing discovery_task queue with status and source filters."
todos:
  - id: client
    content: "discoveryAdminApi.listTasks"
    status: pending
  - id: page
    content: "DiscoveryTasksPage table + QueryStatusView"
    status: pending
isProject: false
---

# Chapter 5 — Crawler targets table

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/discovery-layer-crawler-queue-ui` · **Status:** planned

**Depends on:** [2](02-admin-discovery-api.md), [4](04-admin-shell-email-gate.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Operators see what fetch work is queued at `/admin/discovery/tasks` — target URL, status, source, priority,
lease expiry.

## Design decisions

Reuse documents-list patterns: `useDiscoveryTasksQuery`, skeleton, error state.

Default filter: `status=pending`.

## Files

| Path | Change |
| --- | --- |
| `apps/web/src/features/discovery-admin/services/discoveryAdminApi.ts` | API client |
| `apps/web/src/features/discovery-admin/containers/DiscoveryTasksPage.tsx` | Page |
| `apps/web/src/features/discovery-admin/components/DiscoveryTasksTable.tsx` | Table |
| `apps/web/src/features/discovery-admin/**/*.test.tsx` | Tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `DiscoveryTasksPage · renders rows from mocked admin tasks API` | Happy path |
| `DiscoveryTasksPage · shows error state when query fails` | Negative |

## Green

1. API client + hook with MSW/fixtures.
2. Table + page; tests 1–2.

## Refactor gate

Table columns in one component; page orchestrates query only. Report outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin/containers/DiscoveryTasksPage.test.tsx
cd ../.. && ./ci.sh
```

## Out of scope

Claim actions from UI (read-only admin D6).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-crawler-queue-ui
```

```text
test(web): discovery tasks admin table

feat(web): add discovery crawler targets page
```

Open PR into `feat/plans-discovery-layer`.
