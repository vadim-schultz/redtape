---
name: "Chapter 5 — Embedding task machine API"
overview: "Expose lease-based claim, complete, fail, release and summary routes for embedding tasks so workers can embed candidate text without database access, rejecting stale vectors safely."
id: C5
depends_on:
  - C4
touches:
  - apps/api/app/features/search/
  - apps/api/app/schema/search/
  - apps/api/app/main.py
  - apps/api/app/features/discovery/router.py
  - apps/api/scripts/export_machine_contract.py
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: queue
    content: "Claim embedding tasks with FOR UPDATE SKIP LOCKED and a lease; reclaim expired leases."
    status: pending
  - id: complete
    content: "Validate and store vectors per item, discarding stale hashes and re-enqueueing."
    status: pending
  - id: fail-release
    content: "Implement fail with bounded retries and backoff, and release without consuming an attempt."
    status: pending
  - id: routes
    content: "Add machine routes, schemas and a queue summary; honour the database soft limit."
    status: pending
  - id: tests
    content: "Add concurrency, stale, dimension, retry, release and contract tests."
    status: pending
---

# Chapter 5 — Embedding task machine API

**Repo:** `redtape` (`apps/api`)
**Depends on:** [Chapter 4](04-search-text-builder-and-backfill.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Give embedding workers a small, safe HTTP contract. Workers never see the database: they claim work, embed the text they were given, and post vectors back.

## Design decisions

- Routes under the existing machine prefix, authenticated by the same `X-API-Key` dependency as `machine_controller.py`:
  - `POST /api/v1/discovery/machine/embeddings/claim` `{limit, model}` → tasks `{task_id, candidate_id, text, text_hash, lease_expires_at}`;
  - `POST …/embeddings/complete` `{items: [{task_id, text_hash, model, vector}]}` → per-item `stored | stale | rejected`;
  - `POST …/embeddings/fail` `{task_id, error, retryable}`; `POST …/embeddings/release` `{task_ids}`;
  - `GET …/embeddings/summary` → `pending_ready`, `claimed`, `failed`, `stale_candidates` for the workflow's early exit.
- **Claim** selects pending tasks that are claimable (`not_before` null or past), ordered by `(priority, created_at, id)`, with `FOR UPDATE SKIP LOCKED`, sets `claimed`, `claimed_at`, `lease_expires_at` (the 15-minute lease constant used by `discovery/task_queue.py`), increments `attempt_count`, and first reclaims expired leases (re-pend, or fail at the attempt cap). This is the repository's first `SKIP LOCKED` claim, so it gets a concurrency test.
- **Complete** per item, in one transaction:
  1. unknown task or not claimed by this key → `rejected`;
  2. `model` differs from the task's, or vector length differs from `EMBEDDING_DIM`, or any value is not finite → `rejected` (the task is failed non-retryably, with the reason);
  3. `text_hash` differs from the candidate's current `candidate_search_text.content_hash` → `stale`: discard the vector, mark the task completed, and enqueue a fresh task for the current hash;
  4. otherwise upsert `candidate_embedding` by `(candidate_id, model, locale)` and complete the task.
  One bad item never fails the batch.
- **Fail** reuses the retry policy of `discovery/task_retry.py` (`MAX_ATTEMPTS = 3`, backoff 5 min / 30 min / 3 h) when `retryable`; otherwise marks failed. **Release** returns tasks to pending and gives the attempt back (`hand_back` semantics), used on quota stops.
- Writes (`claim` is a write, `complete` writes rows) honour the database soft limit through `features/discovery/db_headroom.py`: answer 507 as the existing machine writes do.
- Request size: `limit` is capped (default 50); `complete` bodies are bounded (about 50 vectors × `EMBEDDING_DIM` floats). A larger body is rejected with 413.
- Retry constants and lease helpers are imported from the existing discovery modules; if they are bound to `DiscoveryTask`, extract the small generic part rather than copying it, and keep the discovery behaviour unchanged (its tests must still pass).
- New schemas in `app/schema/search/`; the machine contract fixture (`scripts/export_machine_contract.py`, consumed by the ingest tests) is regenerated.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/search/queue.py` | Claim, reclaim, complete, fail, release over `embedding_task`. |
| `apps/api/app/features/search/machine_controller.py`, `router.py` | Routes; registered next to the discovery machine router (`app/main.py`, `features/discovery/router.py` show the pattern). |
| `apps/api/app/schema/search/machine.py` | Request and response models. |
| `apps/api/app/features/discovery/task_retry.py`, `task_lease.py` | Only if a generic extraction is needed. |
| `apps/api/scripts/export_machine_contract.py` | Include the new routes. |
| `apps/api/tests/test_embedding_queue.py` | Claim, lease, reclaim, concurrency. |
| `apps/api/tests/test_embedding_complete.py` | Stored, stale, rejected. |
| `apps/api/tests/test_embedding_machine_api.py` | Routes, auth, 507, 413, summary. |

## Red tests

### Happy path

- `claim · two concurrent claimers never receive the same task` (real transactions, `SKIP LOCKED`).
- `claim · reclaims an expired lease and respects not_before and priority`.
- `complete · stores a vector and completes the task` and the vector is searchable by cosine distance.
- `release · returns tasks to pending without consuming an attempt`.
- `summary · reports pending_ready for the workflow's early exit`.

### Negative path

- `complete · a stale hash is discarded and a fresh task is queued` asserts no `candidate_embedding` row for the old hash.
- `complete · wrong dimension, wrong model or non-finite values are rejected` per item, other items still stored.
- `complete · a task claimed by another key is rejected`.
- `fail · retryable failures back off and stop at the attempt cap; non-retryable fail immediately`.
- `claim · answers 507 at the database soft limit` and `complete · oversize body answers 413`.
- `auth · missing or wrong API key is refused`.

## Green

1. Implement the queue against the repository tests.
2. Add `complete` with the validation order above.
3. Add routes, schemas and the summary; regenerate the machine contract.

## Refactor gate

- Controllers contain no SQL or business rules; the queue module owns state transitions.
- One state-transition table for task status, not scattered `if` chains.
- Retry and lease logic shared with discovery, not duplicated.
- No boolean parameters; typed result models for the per-item outcomes.
- Existing discovery queue tests still pass unchanged.

## Verification

```bash
cd apps/api
uv run pytest tests/test_embedding_queue.py tests/test_embedding_complete.py \
  tests/test_embedding_machine_api.py tests/test_discovery_task_queue.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run python scripts/export_machine_contract.py
cd ../.. && ./ci.sh
```

Record the concurrency test result and the regenerated contract fixture in [../run-ledger.md](../run-ledger.md).

## Out of scope

The worker, Workers AI calls, neuron metering (chapter 6), the query path, any public route.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/embedding-task-api
```

```text
test(api): describe embedding task claim, complete and release
feat(api): add embedding task machine routes
```
