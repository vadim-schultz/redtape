---
name: "Chapter 14 — Translation queue and machine API"
overview: "Enqueue translation work when candidate text appears or changes, and expose lease-based claim, complete, fail, release and summary routes that store each translation once, discard stale results and never overwrite human translations."
id: C14
depends_on:
  - C5
  - C13
touches:
  - apps/api/app/features/translation/
  - apps/api/app/schema/translation/
  - apps/api/app/features/discovery/
  - apps/api/app/features/search/leased_queue.py
  - apps/api/app/main.py
  - apps/api/scripts/
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: enqueue
    content: "Enqueue translation tasks per target locale when a candidate's translation unit is new, changed or missing, with confidence-based priority."
    status: pending
  - id: routes
    content: "Add claim, complete, fail, release and summary routes on the shared leased queue."
    status: pending
  - id: complete-rules
    content: "Store a translation once; discard stale results; never overwrite a human translation; validate and bound the text."
    status: pending
  - id: hook
    content: "Publish a translation-stored event that later chapters subscribe to."
    status: pending
  - id: backfill
    content: "Add a resumable backfill that enqueues missing translations."
    status: pending
  - id: tests
    content: "Add enqueue, priority, concurrency, stale, human-protection, bounds and contract tests."
    status: pending
---

# Chapter 14 — Translation queue and machine API

**Repo:** `redtape` (`apps/api`)
**Depends on:** [Chapter 5](05-embedding-task-machine-api.md), [Chapter 13](13-translation-schema-and-core.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Give translation workers the same safe contract the embedding workers have, and decide which candidates get translated, into which locales, in which order.

## Design decisions

- New feature folder `apps/api/app/features/translation/` (`enqueue.py`, `queue.py`, `service.py`, `machine_controller.py`, `router.py`); schemas in `app/schema/translation/`.
- **Enqueue.** For each candidate and each locale in `TRANSLATION_TARGET_LOCALES`: compute the current `source_hash` of the translation unit (chapter 13's function over the German title and the card description). Enqueue a pending task when there is no `candidate_translation` row, or when the stored `source_hash` differs (stale re-translation). Idempotent through the partial unique index; a changed hash updates a pending task's `source_hash` and leaves a claimed task alone (its result is then rejected as stale and re-queued). Hooked into the same candidate and mention write paths as chapter 4 (a one-line call each).
- **Priority.** Higher-confidence candidates first: priority is derived from the candidate's confidence band at enqueue time (a single-candidate evaluation of the existing score relation, not the list query); stale re-translations get a lower priority than first translations; all locales of one candidate share a priority so a candidate is finished across languages before lower-priority ones start (fair share).
- **Routes** under the machine prefix and API-key dependency, built on chapter 5's `leased_queue.py`:
  - `POST …/translations/claim` `{limit}` → tasks `{task_id, candidate_id, locale, source_locale: "de", title, description, source_hash, lease_expires_at}`;
  - `POST …/translations/complete` `{items: [{task_id, source_hash, title, description, model}]}` → per item `stored | stale | rejected`;
  - `POST …/translations/fail`, `…/release`, `GET …/translations/summary` (`pending_ready`, `claimed`, `failed`, `stale`, `translated` per locale).
- **Complete rules**, per item, in one transaction:
  1. unknown task, or not claimed by this key → `rejected`;
  2. text fails bounds (title non-empty and at most 300 characters, description at most 4000, control characters stripped by the same validators the suggestion payloads use) → `rejected`, task failed non-retryably with the reason;
  3. `source_hash` differs from the current hash → `stale`: discard, complete the task, enqueue a fresh one;
  4. a `human` row already exists for `(candidate, locale)` → `rejected` with reason `human_exists` (never overwritten, invariant 9);
  5. otherwise upsert `candidate_translation` with `source = mt`, the model and hash, and complete the task.
- **Event.** After a translation is stored the service calls `on_translation_stored(candidate_id, locale)` through a small subscriber list. This chapter ships the mechanism and a no-op default; chapter 16 subscribes the search-text refresh, so translated text becomes searchable without a code change here.
- **Backfill.** `apps/api/scripts/backfill_translations.py`: keyset pagination over candidates, resumable by `--after`, optional `--locale`, prints counts (enqueued, up to date, stale). It calls the same `enqueue`.
- Writes honour the database soft limit (507); `limit` and body sizes are bounded (413).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/translation/enqueue.py`, `queue.py`, `service.py`, `machine_controller.py`, `router.py` | Feature. |
| `apps/api/app/features/search/leased_queue.py` | Reused; extend only if a gap appears. |
| `apps/api/app/schema/translation/machine.py` | Request and response models. |
| `apps/api/app/features/discovery/candidate_emit*.py`, `mention_rows.py`, `candidate_service.py` | One-line enqueue calls beside chapter 4's hook. |
| `apps/api/app/main.py`, `features/discovery/router.py` | Router registration. |
| `apps/api/scripts/backfill_translations.py`, `export_machine_contract.py` | Backfill; contract. |
| `apps/api/tests/test_translation_enqueue.py`, `test_translation_complete.py`, `test_translation_machine_api.py`, `test_backfill_translations.py` | Tests. |

## Red tests

### Happy path

- `enqueue · a new candidate gets one pending task per target locale` and re-running changes nothing.
- `enqueue · a changed source hash re-queues at lower priority; a claimed task is left alone`.
- `priority · higher-confidence candidates are claimed first and all locales of one candidate stay together`.
- `claim · two concurrent claimers never receive the same task` (reusing the shared queue).
- `complete · stores a translation once and completes the task`; the stored-event subscriber is called once.
- `summary · reports pending_ready and translated counts per locale`.
- `backfill · enqueues only missing or stale translations and is idempotent`.

### Negative path

- `complete · a stale hash is discarded and re-queued`.
- `complete · a human translation is never overwritten` (`rejected: human_exists`).
- `complete · over-long, empty or control-character text is rejected without failing other items`.
- `complete · a task claimed by another key is rejected`.
- `fail · retryable failures back off and stop at the attempt cap`.
- `routes · 507 at the database soft limit, 413 on oversize bodies, 401 without a key`.

## Green

1. Enqueue and priority against the tests.
2. Routes, complete rules, event mechanism.
3. Backfill; regenerate the machine contract fixture.

## Refactor gate

- Queue mechanics are not duplicated from chapter 5; shared helper only.
- The complete rules are an ordered, table-like list of small checks, not nested branches.
- No boolean parameters; typed per-item outcomes.
- Controllers contain no SQL or business rules.

## Verification

```bash
cd apps/api
uv run pytest tests/test_translation_enqueue.py tests/test_translation_complete.py \
  tests/test_translation_machine_api.py tests/test_backfill_translations.py \
  tests/test_embedding_queue.py tests/test_discovery_task_queue.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run python scripts/export_machine_contract.py
cd ../.. && ./ci.sh
```

Record the regenerated contract, the concurrency result and the backfill counts in [../run-ledger.md](../run-ledger.md).

## Out of scope

The worker that translates (chapter 15), search text and embeddings for translated locales (chapter 16), serving translations to clients (chapter 17), a human-edit endpoint.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/translation-task-api
```

```text
test(api): describe translation enqueue, priority and completion rules
feat(api): add translation tasks and machine routes
feat(api): add translation backfill script
```
