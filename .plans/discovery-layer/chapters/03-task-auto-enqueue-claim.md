---
name: "Chapter 3 — Task auto-enqueue + claim"
overview: "Machine catalogue batch upsert with auto-enqueued fetch tasks, task claim/complete/fail, fetch log append — all behind X-API-Key."
todos:
  - id: upsert
    content: "POST /catalogue/batch + discovery_event"
    status: pending
  - id: enqueue
    content: "Auto-enqueue fetch_url task when portal_url present"
    status: pending
  - id: claim
    content: "POST /tasks/claim with lease"
    status: pending
isProject: false
---

# Chapter 3 — Task auto-enqueue + claim

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-layer-task-queue` · **Status:** planned

**Depends on:** [1](01-staging-migration-lineage.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §4 machine · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Ingest workers upsert catalogue rows and claim work without database access. Upsert enqueues a `fetch_url`
task when `portal_url` is set (D5). Claim is testable with API tests only — no crawler package.

## Design decisions

**Slice A — upsert:** Idempotent on `(source, external_id)`; updates `raw_payload` and `updated_at`;
writes `catalogue_upserted` and `task_enqueued` events.

**Slice B — claim:** `POST /tasks/claim` assigns up to `limit` pending tasks ordered by
`priority, created_at`; sets `claimed_by_api_key_id`, `lease_expires_at` (e.g. 15 minutes).

**Slice C — progress:** `complete`, `fail`, `fetches` endpoints update task status and append fetch log.

**Auth:** `require_machine` only on machine router prefix.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/machine_controller.py` | Machine handlers |
| `apps/api/app/features/discovery/service.py` | Upsert, enqueue, claim logic |
| `apps/api/app/schema/discovery/*.py` | Request/response DTOs |
| `apps/api/tests/test_discovery_machine_api.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `POST /catalogue/batch · upserts row and creates pending fetch task when portal_url set` | Happy path |
| `POST /catalogue/batch · returns 401 without API key` | Negative |
| `POST /catalogue/batch · returns 422 for missing external_id` | Negative |
| `POST /tasks/claim · assigns pending tasks to the caller key` | Happy path |
| `POST /tasks/claim · returns empty list when queue drained` | Happy path edge |
| `POST /tasks/{id}/fetches · appends fetch log and leaves task claimed` | Happy path |

## Green

1. Batch upsert + events; tests 1–3.
2. Claim + lease; tests 4–5.
3. Complete/fail/fetch log; test 6.

## Refactor gate

Enqueue rules in `_enqueue_tasks_for_service()`; claim in `_claim_pending_tasks()` — no nested if chains
for status. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_machine_api.py
cd ../.. && ./ci.sh
```

## Out of scope

Entity/claim machine endpoints (used in chapter 17/20 pointer), admin pipeline aggregate (chapter 6).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-task-queue
```

```text
test(api): describe discovery machine upsert and claim

feat(api): add discovery catalogue batch and task claim API
```

Open PR into `feat/plans-discovery-layer`.
