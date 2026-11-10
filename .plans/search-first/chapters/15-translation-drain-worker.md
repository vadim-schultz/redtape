---
name: "Chapter 15 — Translation drain worker"
overview: "Add the translate drain: a Python CLI worker on GitHub Actions that claims translation tasks, translates the title and description with the chapter 13 engine within the shared neuron budget while leaving headroom for query embedding, and posts results back."
id: C15
depends_on:
  - C13
  - C14
touches:
  - apps/discovery-ingest/discovery_ingest/translation/
  - apps/discovery-ingest/discovery_ingest/worker/
  - apps/discovery-ingest/discovery_ingest/client/
  - apps/discovery-ingest/discovery_ingest/cli/translate/
  - apps/discovery-ingest/tests/
  - .github/workflows/discovery-translate.yml
  - docs/operations/scheduled-jobs.md
  - docs/operations/gha-budget.md
  - apps/discovery-ingest/README.md
execution: chapter-implementer
todos:
  - id: client-api
    content: "Add machine API client methods for translation claim, complete, fail, release and summary."
    status: pending
  - id: drain
    content: "Add the translate drain loop with batching, validation, one repair attempt, per-item settlement and stop reasons."
    status: pending
  - id: budget
    content: "Meter neurons through the shared ledger and keep a reserved floor for request-time query embedding."
    status: pending
  - id: workflow
    content: "Add the discovery-translate workflow with precheck, early exit and minutes report."
    status: pending
  - id: tests
    content: "Add batching, validation, repair, metering, floor, stop-reason and stale tests with fake transports."
    status: pending
---

# Chapter 15 — Translation drain worker

**Repo:** `redtape` (`apps/discovery-ingest`, `.github`, `docs/operations`)
**Depends on:** [Chapter 13](13-translation-schema-and-core.md), [Chapter 14](14-translation-queue-and-machine-api.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Translate every candidate's title and description into each target locale once, using free neurons, without ever touching the database and without starving the query-time embedding of its budget.

## Design decisions

- A sibling drain beside `worker/drain.py` and chapter 6's embed drain, reusing `DrainPolicy`, the stop reasons (`queue_empty`, `batch_limit`, `time_budget`, `llm_budget`, `llm_quota`, `db_limit`, `error`) and the `DrainReport` the workflows parse. Client methods in `client/translation_api.py` in the style of the other `*_api.py` modules.
- **Batching.** Claim up to about 10 tasks per batch, group by locale (one prompt per locale and batch), translate through the engine built from `TRANSLATION_ENGINE` (chapter 13's `TranslationEngine` port and registry; the drain names no provider) with the per-locale glossary, run the base validators.
- **Validation and repair.** A unit that fails a validator gets one repair request that states the violated rule; if it still fails the task is failed non-retryably with the reason (a human can review those), never stored. Valid results are posted with `complete`.
- **Per-item settlement.** `stored` and `stale` need nothing more; `rejected` is logged with the reason and counted in the report; `unavailable` (object storage down, chapter 14) is counted and the task has already been handed back, so the drain stops the batch cleanly instead of retrying in a loop. Results are posted with the engine's `name` and `model`.
- **Budget.** Reserve before each batch through the `UsageMeter` that matches the engine's usage unit (today `NeuronUsageMeter` over `NeuronMeter`/`ledger_reserve.py`, estimating with the engine's `estimate(batch)`), settle to the reported usage, refund on failure. **Reserved floor:** for a neuron-metered engine the drain stops with `llm_budget` when the ledger's remaining neurons would fall below `QUERY_EMBED_RESERVE`, so request-time query embedding (decision D1) always has headroom; an engine billed in another unit is bounded by its own meter instead and the floor does not apply to it; the embed drain (chapter 6) is cheap and unaffected. A quota error stops with `llm_quota` and **releases** unprocessed tasks without consuming attempts.
- **Ordering and fairness.** Tasks arrive in priority order from chapter 14 (high-confidence candidates first, all locales of a candidate together), so a partially complete run still leaves the most important candidates fully translated.
- **CLI.** `python -m discovery_ingest translate drain [--max-tasks N --time-budget S --neuron-budget N]` prints one JSON `DrainReport`; exit codes as the other drains.
- **Workflow** `.github/workflows/discovery-translate.yml` copies `discovery-drain.yml`: `schedule` plus `workflow_dispatch`, gated by repo variable `DISCOVERY_TRANSLATE_SCHEDULE == 'enabled'`, shared `concurrency: discovery-pipeline` (`cancel-in-progress: false`), `budget show --require-remaining …` precheck, `wait_for_api`, early exit when `GET …/translations/summary` reports `pending_ready = 0`, the drain with `tee drain-report.json`, a step summary, failure only if `succeeded` is false, an `if: always()` minutes report. It is scheduled after the embed drain within the same day so fresh translations are embedded promptly; cadence and per-run caps are chosen against `docs/operations/gha-budget.md` and the chapter 13 projection (record both in the ledger).
- The Workers AI token is a GitHub secret, never printed; `_scrub` behaviour is covered by a test.
- Docs: `scheduled-jobs.md`, `gha-budget.md`, ingest README.

## Files

| Path | Change |
| --- | --- |
| `apps/discovery-ingest/discovery_ingest/client/translation_api.py` | Machine API client. |
| `apps/discovery-ingest/discovery_ingest/worker/translate_drain.py`, `translate_batch.py`, `translate_settle.py` | Drain, batch step, settlement. |
| `apps/discovery-ingest/discovery_ingest/translation/repair.py` | One repair attempt. |
| `apps/discovery-ingest/discovery_ingest/cli/translate/` | `translate drain` next to `translate probe`. |
| `.github/workflows/discovery-translate.yml` | New workflow. |
| `docs/operations/scheduled-jobs.md`, `gha-budget.md`, `apps/discovery-ingest/README.md` | Docs. |
| `apps/discovery-ingest/tests/test_translate_drain.py`, `test_translate_repair.py`, `test_translation_api_client.py` | Tests. |

## Red tests

### Happy path

- `translate drain · claims, translates per locale, validates and completes` with report counts.
- `translate drain · a failing unit is repaired once and then stored`.
- `translate drain · stored and stale outcomes are both counted`.
- `translate drain · meter reserves before and settles to usage`.
- `translate drain · stops with queue_empty`.
- `translate drain · builds the engine from the registry and posts its name and model` (a fake registered adapter proves the drain names no provider).

### Negative path

- `translate drain · a unit that still fails validation after repair is failed non-retryably and never stored`.
- `translate drain · stops with llm_budget when the reserved query-embedding floor would be breached`.
- `translate drain · quota exhaustion stops with llm_quota and releases unprocessed tasks without burning attempts`.
- `translate drain · an unavailable item ends the batch with the tasks already handed back`.
- `translate drain · an engine with a non-neuron usage unit is metered by its own meter and skips the query-embedding floor` (fake engine and meter).
- `translate drain · a 5xx fails the batch retryably; a 401 stops as infrastructure; 507 stops with db_limit`.
- `translate drain · a short response (fewer results than units) fails the batch, not individual silently dropped items`.
- `secrets · the token never appears in logs or the report`.

## Green

1. Client methods and the repair step.
2. Drain, metering and the floor.
3. CLI and workflow; run once with `workflow_dispatch` against a non-production API when available.
4. Update the docs with cadence and measured minutes per run.

## Refactor gate

- No logic duplicated from the other drains: shared pieces are imported or extracted with the existing drain tests green.
- Functions about 5 lines, at most 3 parameters, no `Any`, no boolean flags.
- The workflow differs from `discovery-drain.yml` only in queue, summary and variable names.
- Repair and validation are the core's functions, not re-implemented here.

## Verification

```bash
cd apps/discovery-ingest
uv run pytest tests/test_translate_drain.py tests/test_translate_repair.py tests/test_translation_api_client.py
uv run ruff format --check . && uv run ruff check . && uv run mypy .
cd ../.. && ./ci.sh
```

After merge (operator): run the chapter 14 backfill, set `DISCOVERY_TRANSLATE_SCHEDULE=enabled`, dispatch the workflow, and record the first report, neurons spent, validator failure rate, Actions minutes per run and translated/total per locale in [../run-ledger.md](../run-ledger.md).

## Out of scope

Search text and embeddings for the translations (chapter 16), the pop-over (chapter 17), human review tooling, a Cloudflare-hosted worker runtime.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/translation-drain-worker
```

```text
test(ingest): describe translation drain, repair and budget floor
feat(ingest): add translate drain on Workers AI
ci: add the discovery-translate workflow
```
