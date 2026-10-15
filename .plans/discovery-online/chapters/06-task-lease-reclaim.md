---
name: "Chapter 6 — Task lease reclaim"
overview: "Expired claimed tasks return to pending so GHA drain can recover stuck work."
todos:
  - id: reclaim
    content: "Reclaim expired leases before claim or in claim_tasks"
    status: pending
  - id: tests
    content: "Machine API tests for expired lease"
    status: pending
isProject: false
---

# Chapter 6 — Task lease reclaim

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-online-lease-reclaim` · **Status:** planned

**Depends on:** [5](05-ingest-idempotency.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

When a worker dies mid-lease, `discovery_task` rows stuck in `claimed` with `lease_expires_at < now` become claimable again. Scheduled drain jobs make forward progress without manual DB edits.

## Design decisions

**Reclaim timing:** at start of `claim_tasks` (or in `list_pending_tasks_for_claim`), reset `status=pending`, clear `claimed_by_api_key_id`, null lease fields.

**Do not reclaim** tasks still inside active lease.

**Events:** optional `task_enqueued` or document reclaim as silent state transition only.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/repository.py` | `reclaim_expired_claims(now)` |
| `apps/api/app/features/discovery/service.py` | Call reclaim before claim |
| `apps/api/tests/test_discovery_machine_api.py` | Expired lease tests |

## TDD loop

| Test | Asserts |
| --- | --- |
| `claim_tasks · reclaims expired claimed task` | Happy path |
| `claim_tasks · does not reclaim task with future lease` | Negative path |

## Refactor gate

Reclaim in repository; service orchestrates. Report outcome.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_machine_api.py -k lease
cd ../.. && ./ci.sh
```

## PR

Target loop branch.
