---
name: "Chapter 6 — Embedding drain worker"
overview: "Add the embed drain: a Python CLI worker on GitHub Actions that claims embedding tasks, embeds them on Cloudflare Workers AI with Qwen3-Embedding within the shared neuron budget, and posts vectors back."
id: C6
depends_on:
  - C1
  - C5
touches:
  - apps/discovery-ingest/discovery_ingest/extract/embedding/
  - apps/discovery-ingest/discovery_ingest/extract/llm/prices.py
  - apps/discovery-ingest/discovery_ingest/worker/
  - apps/discovery-ingest/discovery_ingest/client/
  - apps/discovery-ingest/discovery_ingest/cli/embed/
  - apps/discovery-ingest/tests/
  - .github/workflows/discovery-embed.yml
  - docs/operations/scheduled-jobs.md
  - docs/operations/gha-budget.md
  - apps/discovery-ingest/README.md
execution: chapter-implementer
todos:
  - id: client-api
    content: "Add machine API client methods for embedding claim, complete, fail, release and summary."
    status: pending
  - id: metering
    content: "Price the embedding model and reserve, settle and refund neurons through the shared ledger."
    status: pending
  - id: drain
    content: "Add the embed drain loop with batching, stop reasons and per-item settlement."
    status: pending
  - id: workflow
    content: "Add the discovery-embed GitHub Actions workflow with ledger precheck, early exit and minutes report."
    status: pending
  - id: tests
    content: "Add batching, metering, stop-reason, stale and retry tests with fake transports."
    status: pending
---

# Chapter 6 — Embedding drain worker

**Repo:** `redtape` (`apps/discovery-ingest`, `.github`, `docs/operations`)
**Depends on:** [Chapter 1](01-infra-and-embedding-probe.md), [Chapter 5](05-embedding-task-machine-api.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Compute embeddings whenever free neurons are available, without the worker ever touching the database. Reuse the existing drain machinery wherever it applies: policy, stop reasons, ledger, throttle and error taxonomy.

## Design decisions

- The embedding queue is not a `discovery_task` kind, so this is a sibling drain beside `worker/drain.py` rather than a new entry in `handler_table.py`. It reuses `DrainPolicy` (`neuron_budget`, `time_budget_seconds`, `max_tasks`, `max_batches`), the stop reasons (`queue_empty`, `batch_limit`, `time_budget`, `llm_budget`, `llm_quota`, `db_limit`, `error`) and the `DrainReport` JSON the workflows already parse.
- Client: `discovery_ingest/client/embedding_api.py` (methods for the five routes) in the style of the other `*_api.py` modules, over the existing `http_client.py` (`X-API-Key`, scrubbed errors).
- Embedding: extend chapter 1's `CloudflareEmbeddingClient` with batching to `min(probe batch limit, 50)` and the same `Throttle`. **Documents are embedded raw** (no instruction prefix); the instruction prefix is for queries only (chapter 8). Tasks carry a `locale` and the text for that locale (German canonical text now, translated text after chapter 16); the drain treats them identically and posts back by task id.
- Metering: add the model's price (about 1075 neurons per million input tokens, confirm from the probe and Cloudflare's price page) to `extract/llm/prices.py`. Reserve before each batch through `NeuronMeter`/`ledger_reserve.py` using a conservative token estimate (characters ÷ 3), settle to the reported usage, refund on failure. Output tokens are not billed for embeddings.
- Per-batch flow: claim → embed → `complete`. Per-item results: `stored` and `stale` need nothing more; `rejected` is logged with the reason. A `LlmQuotaExceeded`-style error or an exhausted reservation raises the stop reason and **releases** the unprocessed tasks so attempts are not burned; a retryable HTTP error fails the batch's tasks as retryable; an auth error stops the drain as infrastructure.
- CLI: `python -m discovery_ingest embed drain [--max-tasks N --time-budget S --neuron-budget N]` prints one JSON `DrainReport`; exit codes follow the existing convention.
- Workflow `.github/workflows/discovery-embed.yml` copies the structure of `discovery-drain.yml`: `schedule` plus `workflow_dispatch`, gated by repo variable `DISCOVERY_EMBED_SCHEDULE == 'enabled'`, shared `concurrency: discovery-pipeline` (`cancel-in-progress: false`), `budget show --require-remaining …` precheck, `wait_for_api`, **an early exit when `GET …/embeddings/summary` reports `pending_ready = 0`** (saves Actions minutes), the drain with `tee drain-report.json`, a step summary, failure only if `succeeded` is false, and an `if: always()` minutes report.
- Cadence is chosen against `docs/operations/gha-budget.md` in this chapter (shipped as twice a day, 06:10 and 18:10 UTC; see gha-budget.md); the Workers AI token is a GitHub secret, never printed.
- Docs updated: `docs/operations/scheduled-jobs.md`, `gha-budget.md`, `apps/discovery-ingest/README.md`.

## Files

| Path | Change |
| --- | --- |
| `apps/discovery-ingest/discovery_ingest/client/embedding_api.py` | Machine API client methods. |
| `apps/discovery-ingest/discovery_ingest/extract/embedding/client.py` | Batching and settle-ready usage. |
| `apps/discovery-ingest/discovery_ingest/extract/embedding/meter.py` | Reserve, settle, refund via `NeuronMeter`. |
| `apps/discovery-ingest/discovery_ingest/extract/llm/prices.py` | Embedding model price. |
| `apps/discovery-ingest/discovery_ingest/worker/embed_drain.py`, `embed_batch.py`, `embed_settle.py` | Drain loop, batch step, settlement. |
| `apps/discovery-ingest/discovery_ingest/cli/embed/` | `embed drain` command next to `embed probe`. |
| `.github/workflows/discovery-embed.yml` | New workflow. |
| `docs/operations/scheduled-jobs.md`, `docs/operations/gha-budget.md`, `apps/discovery-ingest/README.md` | Docs. |
| `apps/discovery-ingest/tests/test_embed_drain.py`, `test_embed_meter.py`, `test_embedding_api_client.py` | Tests. |

## Red tests

### Happy path

- `embed drain · claims, embeds in batches and completes` asserts batch sizes, vector order, and the report counts.
- `embed meter · reserves before and settles to actual usage` asserts the ledger is charged the settled amount.
- `embed drain · stale and stored results are both counted` and nothing else is retried.
- `embed drain · stops with queue_empty`.

### Negative path

- `embed drain · quota exhaustion stops with llm_quota and releases the unprocessed tasks` asserts no attempt is consumed.
- `embed drain · an exhausted reservation stops with llm_budget before any call`.
- `embed drain · a 5xx fails the batch retryably; a 401 stops as infrastructure`.
- `embed drain · the 507 soft limit stops with db_limit`.
- `embed client · a short response (fewer vectors than texts) fails the batch, not individual silently-dropped items`.
- `workflow · documents the skip when pending_ready is 0` (a script-level test of the precheck helper).

## Green

1. Add the API client methods and the metering.
2. Implement the drain on the existing policy and report types.
3. Add the CLI command and the workflow; run once with `workflow_dispatch` against a non-production API when available.
4. Update the docs with the chosen cadence and measured minutes per run.

## Refactor gate

- No logic duplicated from `worker/drain.py`/`batch.py`: shared pieces are imported or extracted with the existing drain tests still green.
- Functions about 5 lines, at most 3 parameters (use the policy and report DTOs), no `Any`, no boolean flags.
- The workflow matches `discovery-drain.yml` except for the queue, summary and variable names.
- Secrets never appear in logs or reports (`_scrub` behaviour covered by a test).

## Verification

```bash
cd apps/discovery-ingest
uv run pytest tests/test_embed_drain.py tests/test_embed_meter.py tests/test_embedding_api_client.py
uv run ruff format --check . && uv run ruff check . && uv run mypy .
cd ../.. && ./ci.sh
```

After merge (operator): set `DISCOVERY_EMBED_SCHEDULE=enabled`, run the chapter 4 backfill, dispatch the workflow, and record the first drain report, neurons spent, Actions minutes per run and embedded/total counts in [../run-ledger.md](../run-ledger.md).

## Out of scope

Query embedding (chapter 8), producing per-locale text (chapters 13–16), a Cloudflare-hosted worker runtime.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/embedding-drain-worker
```

```text
test(ingest): describe embedding drain, metering and settlement
feat(ingest): add embed drain on Workers AI
ci: add the discovery-embed workflow
```
