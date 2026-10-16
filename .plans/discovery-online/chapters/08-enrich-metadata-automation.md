---
name: "Chapter 8 — Enrich metadata automation"
overview: "Drain enrich_metadata tasks: FIM steckbrief to entities/claims; optional machine GET catalogue; LeiKa scope."
todos:
  - id: enrich
    content: "enrich_metadata handler in worker"
    status: completed
  - id: machine-read
    content: "Optional GET /catalogue/{id} for machine"
    status: completed
  - id: leika
    content: "LeiKa path or document deferral"
    status: completed
isProject: false
---

# Chapter 8 — Enrich metadata automation

**Repo:** `redtape` (`apps/discovery-ingest`, optional `apps/api`) · **Branch:** `feat/discovery-online-enrich-automation` · **Status:** done

**Depends on:** [7](07-ingest-worker-drain.md), [5](05-ingest-idempotency.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

When drain claims an `enrich_metadata` task (FIM steckbrief URL from [fanout.py](../../../apps/api/app/features/discovery/fanout.py)), the worker fetches JSON, upserts entity and claims via machine API — **without** a local catalogue export file. Claim writes use chapter 5 idempotency.

## Design decisions

**FIM:** parse `fim_id` from `target_url`; reuse [`enrich.py`](../../../apps/discovery-ingest/discovery_ingest/enrich.py) mapping; `post_entity` + `post_claim`.

**Catalogue context:** prefer optional machine `GET /api/v1/discovery/machine/catalogue/{id}` (new route) returning minimal row (`raw_payload`, `source`) for LeiKa segments — or read only from task’s `catalogue_service_id` + stored fanout URL if sufficient.

**LeiKa:** deferred in-loop — worker handles FIM steckbrief only; LeiKa remains on `discovery-ingest leika enrich` CLI until a fanout + worker slice is scheduled.

## Files

| Path | Change |
| --- | --- |
| `apps/discovery-ingest/discovery_ingest/worker/enrich_metadata.py` | Handler |
| `apps/api/app/features/discovery/machine_controller.py` | Optional GET catalogue |
| `apps/api/app/schema/discovery/machine.py` | Read DTO |
| `apps/api/tests/test_discovery_machine_catalogue_read.py` | Tests |
| `apps/discovery-ingest/tests/test_enrich_metadata_worker.py` | MockTransport |

## TDD loop

| Test | Asserts |
| --- | --- |
| `enrich_metadata · fetches steckbrief and posts entity and claim` | Happy path |
| `enrich_metadata · fails task when steckbrief 404` | Negative path |

## Refactor gate

Worker dispatches `fetch_url` vs `enrich_metadata` via registry. Report outcome.

## Verification

```bash
./ci.sh
```

## PR

Target loop branch.
