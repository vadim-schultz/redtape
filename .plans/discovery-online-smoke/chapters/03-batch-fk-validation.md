---
name: "Chapter 3 — Batch FK validation"
overview: "Return 422 when jurisdiction_id FK fails on catalogue batch upsert instead of opaque 500."
todos:
  - id: red
    content: "test_post_catalogue_batch_returns_422_for_unknown_jurisdiction_id"
    status: pending
  - id: green
    content: "Map IntegrityError FK in upsert_catalogue_item"
    status: pending
isProject: false
---

# Chapter 3 — Batch FK validation

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-online-smoke-batch-fk-422` · **Status:** planned

**Depends on:** [01](01-triage-batch-500.md) shows FK violation · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online-smoke`

**Skip** if chapter 1 root cause is not `jurisdiction_id` FK.

---

## Goal

Machine clients get **422** with a clear message when `jurisdiction_id` does not exist — not **500**.

## Design decisions

Handle **foreign key** `IntegrityError` on insert in [`upsert_catalogue_item`](../../../apps/api/app/features/discovery/repository.py) (unique `(source, external_id)` race handling stays as-is). Map to `ClientException` / validation error consistent with Litestar patterns.

## Files

| Path | Change |
| --- | --- |
| [`apps/api/app/features/discovery/repository.py`](../../../apps/api/app/features/discovery/repository.py) | FK `IntegrityError` → domain error |
| [`apps/api/app/features/discovery/service.py`](../../../apps/api/app/features/discovery/service.py) | Only if mapping belongs at service boundary |
| [`apps/api/tests/test_discovery_machine_api.py`](../../../apps/api/tests/test_discovery_machine_api.py) | Happy + negative tests |

## TDD loop

| Test | Asserts |
| --- | --- |
| `test_post_catalogue_batch_returns_422_for_unknown_jurisdiction_id` | Random UUID `jurisdiction_id` → **422**, message mentions jurisdiction |
| `test_post_catalogue_batch_upserts_row_and_creates_pending_fetch_task_when_portal_url_set` | Existing happy path still **201** |

## Refactor gate

Audit `upsert_catalogue_item` and `batch_upsert` containing entity per [refactor-step](../../../.cursor/rules/refactor-step.mdc); report outcome.

## Verification

```bash
cd apps/api && uv run pytest tests/test_discovery_machine_api.py -q
./ci.sh
```

## PR

Target loop branch.
