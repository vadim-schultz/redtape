---
name: "Chapter 5 — Ingest idempotency (OpenPLZ parity)"
overview: "Idempotent fetch_url enqueue, claim dedup/upsert, IntegrityError reconcile, in-batch dedup, double-run tests."
todos:
  - id: enqueue
    content: "Idempotent _enqueue_tasks_for_service"
    status: pending
  - id: claims
    content: "Claim dedup or upsert in repository/service"
    status: pending
  - id: ingest
    content: "Collapse duplicate batch items in discovery-ingest"
    status: pending
  - id: tests
    content: "Double-run machine API tests"
    status: pending
isProject: false
---

# Chapter 5 — Ingest idempotency (OpenPLZ parity)

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`) · **Branch:** `feat/discovery-online-idempotency` · **Status:** planned

**Depends on:** [4](04-scheduled-catalogue-ingest.md) (conceptually before prod schedule) · **Decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md) D9 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

Two identical scheduled ingest runs do not grow pending `fetch_url` tasks or duplicate claims without bound. Behavior aligns with [OpenPLZ import](../../../docs/operations/openplz-import.md): reconcile on **database unique keys** and recover from `IntegrityError` races.

## Design decisions

**`fetch_url` enqueue** ([`service.py`](../../../apps/api/app/features/discovery/service.py) `_enqueue_tasks_for_service`):

- Before `insert_task`, use `find_pending_task` pattern extended to `claimed` for same `(catalogue_service_id, kind, target_url)`.
- Re-enqueue when latest task is `failed` or `target_url` changed on catalogue row.

**Claims** ([`append_claim`](../../../apps/api/app/features/discovery/repository.py)):

- Add `find_claim_by_fingerprint` or upsert: `(discovery_entity_id, kind, payload_fingerprint)`.
- Update payload/confidence in place when fingerprint matches.

**Race safety:** wrap catalogue/entity insert paths with `IntegrityError` → re-select by `(source, external_id)` or entity URL unique.

**Ingest:** `dedupe_batch_items(items) -> list` before POST in `api_client` or CLI.

**Stable external_id:** add regression tests in `test_govdata_client.py` / `test_pvog_client.py` for alias fields.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/repository.py` | Task lookup helpers, claim dedup |
| `apps/api/app/features/discovery/service.py` | Idempotent enqueue, claim path |
| `apps/api/tests/test_discovery_idempotency.py` | Double-run contract |
| `apps/discovery-ingest/discovery_ingest/batch_dedup.py` | In-batch dedup |
| `apps/discovery-ingest/tests/test_batch_dedup.py` | Unit tests |

## TDD loop

| Test | Asserts |
| --- | --- |
| `batch upsert twice · single pending fetch_url task per portal` | Happy idempotency |
| `batch upsert twice · catalogue count unchanged` | Happy path |
| `append_claim twice same fingerprint · one claim row` | Happy path |
| `concurrent catalogue insert · IntegrityError recovers to update` | Negative/race path |

## Refactor gate

Shared helper `enqueue_task_if_needed` used by fanout and fetch_url paths where possible. Report outcome.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_idempotency.py
cd ../.. && ./ci.sh
```

## PR

Target loop branch.
