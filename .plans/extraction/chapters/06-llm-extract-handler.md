---
name: "Chapter E6 — llm_extract handler"
overview: "The llm_extract task handler as a pipeline of named steps (read, decode, clean, reserve, call, ground, post, settle), release instead of fail on quota, budget, storage and database limits, and start guards for the budgeted kind."
todos:
  - id: client
    content: "Machine client methods for the artifact content, taxonomy, mentions and edges"
    status: pending
  - id: handler
    content: "handle_llm_extract pipeline with result notes"
    status: pending
  - id: stops
    content: "Release and stop rules: llm_budget, llm_quota, db_limit, storage"
    status: pending
  - id: guards
    content: "Kind guards: never default, refuses to start without token, budget and ledger"
    status: pending
isProject: false
---

# Chapter E6 — llm_extract handler

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-handler` · **Status:** planned

**Depends on:** [E1](01-staging-groundwork.md), [E2](02-page-cleaner.md), [E3](03-extraction-schema-and-grounding.md), [E4](04-workers-ai-client-and-probe.md), [E5](05-eval-harness-and-model-choice.md), and crawlers [14](../../crawlers/chapters/14-artifact-model-and-api.md), [15](../../crawlers/chapters/15-cloudflare-render-and-snapshot.md), [17](../../crawlers/chapters/17-extractor-framework.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

## Goal

Put the pieces into the queue without letting any limit turn into a failed page. The handler is a short pipeline of named steps like crawlers chapter 15's `render_page`; every step is small and tested.

## Contract

**Kinds.** `llm_extract` joins `DiscoveryTaskKind` in `schemas.py` and the dispatch table in `worker/drain.py`. It is **not** in any default kinds list. A drain whose `--kinds` contains `llm_extract` requires `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_API_TOKEN`, a `--neuron-budget`, a readable ledger (`GET /machine/budgets`) and `GET /machine/artifacts/status` with storage enabled; otherwise it exits non-zero with a clear message **before claiming anything**. `DrainPolicy` gains `neuron_budget`; `StopReason` gains `llm_budget`, `llm_quota` and `db_limit`; `DrainReport` gains `neurons_used`, `llm_calls`, `released` and `ledger_unavailable`. Llm drains claim small batches (default 5) so at most four tasks are released per stop.

**Client.** `DiscoveryMachineClient` gains `get_artifact_content(artifact_id)` (crawlers chapter 14), `get_taxonomy()`, `post_edges(items)` and uses the existing `post_mentions`. A `507` with detail `database_soft_limit` becomes a typed `DatabaseLimitError`.

**Handler** `handle_llm_extract(task, *, client, llm, meter, taxonomy)` runs these named steps; each is a small function:

1. **read:** the task's `artifact_id` (kind `html_snapshot`); a missing artifact fails permanently, a `5xx` fails retryably.
2. **decode:** the crawlers chapter 17 function.
3. **clean:** `clean_page` (E2). Fewer than 200 characters of text completes with note `no_content`.
4. **reserve:** `meter.reserve(...)`. Denied stops the run with `llm_budget` after releasing this task and the unstarted ones; a ledger outage falls back to the run budget (`ledger_unavailable`).
5. **call:** `llm.extract(...)`. `LlmQuotaExceeded` exhausts the day, releases, and stops with `llm_quota`. `LlmInvalidOutput` gets at most one repair attempt if a second reservation is granted, then fails permanently with the model named. `LlmAuthError` releases and fails the run.
6. **ground:** `ground(...)` (E3). Nothing left, or `page_kind` of `login_or_error` or `other`, completes with note `login_wall` or `no_documents` accordingly.
7. **post:** mentions first, then edges (so endpoints exist), in chunks of at most 100; the mention response's `unknown_codes` is added to the diagnostics. `DatabaseLimitError` releases and stops with `db_limit`; storage and 5xx errors fail retryably.
8. **settle:** `meter.settle(...)` with the real token usage, then complete with the grounded counts in the note (for example `docs=7 edges=5 dropped=2`, at most 200 characters).
9. **after:** call the shared screenshot helper of crawlers chapter 19 when at least one mention was posted (wired in [E7](07-wiring-and-workflow.md); here it is an injected callable defaulting to a no-op).

**Release, not fail.** On `llm_budget`, `llm_quota`, `db_limit` and storage problems the drain releases the in-flight task and every claimed but unstarted task (crawlers route `POST /machine/tasks/{id}/release`, no attempt consumed) and stops; the run still succeeds. Only page-level problems fail a task.

**Settle always.** If any step after `reserve` raises, the reservation is settled before the error propagates: with the real usage if a result exists, otherwise adjusted by the estimate only when the call provably did not happen, otherwise left in place (a call that may have been billed is never refunded).

## TDD loops

All tests use a fake `LlmClient`, a fake machine client, a fake ledger and an injected clock.

### Loop A — Pipeline

**Red** (`apps/discovery-ingest/tests/test_llm_extract_worker.py`)

1. `llm_extract reads the snapshot, calls the model once, posts mentions then edges, settles the neurons and completes with a counts note`.
2. `a page with no usable text completes with no_content and never reserves or calls the model`.
3. `a login_or_error or empty extraction completes with login_wall or no_documents and posts nothing`.
4. `mentions are posted before edges, in chunks of at most 100`.
5. `the screenshot helper is called once when at least one mention was posted and not otherwise`.
6. `a missing artifact fails permanently; a 5xx on the content route fails retryably`.
7. `an invalid model output is retried once under a second reservation and then fails permanently naming the model`.

**Green:** one function per step. **Refactor:** about five lines per step; the stop signal is one small exception handled in `_run_batch`.

### Loop B — Stops

**Red** (`test_llm_extract_stops.py`)

1. `a denied reservation releases this task and the unstarted ones and stops with llm_budget`.
2. `a quota error exhausts the day, releases, stops with llm_quota and the run still succeeds`.
3. `a 507 database_soft_limit releases and stops with db_limit`.
4. `an auth error releases and fails the run`.
5. `a reservation is settled with real usage after a successful call and kept when the call may have been billed and then failed`.
6. `an unreachable ledger falls back to the run budget and the report says ledger_unavailable`.

**Green/Refactor:** the stop is one exception type carrying the stop reason.

### Loop C — Kind guards

**Red** (`test_worker_drain.py`, `test_cli_worker.py`)

1. `default kinds exclude llm_extract; the dispatch table contains it`.
2. `draining llm_extract without the token, the neuron budget, a readable ledger or storage fails before claiming anything`.
3. `the drain report includes neurons_used, llm_calls, released and the new stop reasons`.

**Green/Refactor:** one table entry; the guard shares code with the browser-kind guard of crawlers chapter 15.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_llm_extract_worker.py tests/test_llm_extract_stops.py tests/test_worker_drain.py tests/test_cli_worker.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate: deferred to [E7](07-wiring-and-workflow.md), where tasks are enqueued by real snapshots. A dry smoke run is allowed here with one hand-enqueued task: `python -m discovery_ingest worker drain --kinds llm_extract --max-tasks 1 --max-batches 1 --neuron-budget 800`; record the report.

## Out of scope

Enqueueing (E7), the workflow (E7), the admin (E8), editing staged items, retries beyond one repair, batching several pages per call.
