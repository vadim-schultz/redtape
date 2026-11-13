---
name: "Chapter 6 — Azure economy"
overview: "Treat an Azure 429 as a release that does not burn an attempt, pace characters per minute and per day within the free tier, retry chunks instead of whole pages, and measure how often translation memory would hit."
todos:
  - id: rate-limited
    content: "Map 429000 to 429002 to a RateLimited error that carries Retry-After"
    status: pending
  - id: release
    content: "Release a rate-limited batch without consuming an attempt and stop the drain"
    status: pending
  - id: chunk-retry
    content: "Retry each chunk instead of discarding the billed chunks of a page"
    status: pending
  - id: pacing
    content: "Limit characters per minute and pace the daily allowance with carry-over"
    status: pending
  - id: memory-spike
    content: "Measure the block hit rate across stored snapshots before any memory table"
    status: pending
isProject: false
---

# Chapter 6 — Azure economy

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-azure-economy` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 2.4, waste 6) · **Decisions:** D15 · **Gaps:** azure-translation O4 (reset boundary)

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

A 429 from Azure currently burns one of three attempts, the drain moves on to the next page inside the same window, and a 429 on the third chunk of a page throws away the two chunks already billed. The free tier accepts about 33,300 characters a minute on a sliding window, and the adapter sends up to 40,000 in one request. Fix the error model, the per-minute and per-day pacing, and the retry grain.

## Design

- **Error model.** `azure_translator_errors.py` maps codes 429000, 429001 and 429002 to a new `RateLimited(TransientError)` that carries `retry_after` from the `Retry-After` header when Azure sends one (the docs say it may not; the code handles both). `403001` stays `QuotaExceeded`.
- **In-transport retry.** `AzureTransport._post` (`azure_translator_http.py`) retries one chunk up to twice, honouring `Retry-After` and otherwise waiting 2 s, 4 s. Only after that does it raise.
- **Release, not failure.** `translate_settle.failure_of` maps `RateLimited` to a release: `release_task` returns the attempt (`task_lease.py:42-54`), and the drain stops with a new `StopReason` `rate_limited` (`schemas.py:170`). The API's `RunFinishRequest` literal (`schema/discovery/machine.py`) gains the same value. `snapshot_settle.py` does the same. The drain does not re-claim the released tasks in the same run.
- **Chunk memo.** `AzureTranslator._translated` (`translation/adapters/azure_translator.py`) keeps the translated chunks of a page in a memo for the duration of the call, so a retry of a later chunk does not re-bill the earlier ones.
- **Characters per minute.** A sliding-window limiter in `AzureTransport` holds the characters sent in any 60 s window at or below 28,000, which leaves headroom under the 33,300 the free tier enforces. It replaces the fixed 1 s `Throttle` but keeps the 1 s minimum gap.
- **Daily pacing.** The drain computes `remaining_month_chars / days_left_in_month` as its daily allowance and carries over any unspent amount to the next day through the ledger. The daily figure is a setting, `AZURE_DAILY_CHAR_PACE`, defaulting to the computed value.
- **Adaptive share.** The static document share (`snapshot_drain.py`, `DEFAULT_DOCUMENT_BUDGET_SHARE`) becomes a share computed from the pending demand of cards and pages, bounded below by the card band (40%) so cards are never starved.
- **Translation memory, measurement only.** A script reads stored snapshot blocks and reports the share of distinct block hashes across all locales. The result decides whether a memory table is built in a later chapter. No table is added here.

## Files

**Edit**

- `apps/discovery-ingest/discovery_ingest/translation/adapters/azure_translator_errors.py`
- `apps/discovery-ingest/discovery_ingest/translation/adapters/azure_translator_http.py`
- `apps/discovery-ingest/discovery_ingest/translation/adapters/azure_translator.py`
- `apps/discovery-ingest/discovery_ingest/translation/errors.py`
- `apps/discovery-ingest/discovery_ingest/worker/translate_settle.py`
- `apps/discovery-ingest/discovery_ingest/worker/snapshot_settle.py`
- `apps/discovery-ingest/discovery_ingest/operations/snapshot_drain.py`
- `apps/discovery-ingest/discovery_ingest/schemas.py` (the `StopReason` literal)
- `apps/api/app/schema/discovery/machine.py` (the `RunFinishRequest` literal)

**Create**

- `scripts/translation_memory_probe.py` (measurement only)

**Do not edit**

- The ledger's reserve and settle semantics (`character_meter.py`). Refunds already work for non-quota errors (`metered.py:60-61`).

## Red tests

| Test | Asserts |
| --- | --- |
| `a 429 maps to RateLimited with the Retry-After seconds` | Happy: the header value is kept. Negative: a missing header leaves `retry_after` unset. |
| `a rate-limited batch releases its tasks without consuming an attempt` | Happy: attempt count is unchanged after the release. |
| `a rate-limited drain stops and does not re-claim the same tasks` | Negative: the run ends with `rate_limited`; the next claim in the same run returns none of the released tasks. |
| `a retry of chunk three does not re-bill chunks one and two` | Happy: the ledger is charged for each chunk once. |
| `the limiter never sends more than 28,000 characters in any 60 s window` | Happy, with a fake clock and a burst of 50,000 characters. |
| `a 403001 still marks the month exhausted` | Negative: the existing quota behaviour is unchanged. |
| `the daily pace carries an unspent amount to the next day` | Happy: yesterday's unspent characters are added to today's allowance. |

## Green

1. Write the error-mapping tests first. Add `RateLimited`, then the release path.
2. Add the chunk memo test, then the memo.
3. Add the limiter with a fake clock, then the pacing.
4. Write the translation-memory probe last. It is a script with its own tests, not a change to the drain.

## Refactor gate

`AzureTransport._post` must stay under about five lines per method: move the retry, the limiter and the request into three helpers. `snapshot_settle.py` and `translate_settle.py` share one release helper, not two copies.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest -q tests/ -k "azure or translate or snapshot" && cd ../..
cd apps/api && PYTHONPATH=. .venv/bin/python -m pytest -q tests/ -k "discovery and run" && cd ../..
./ci.sh
```

Live gate: before the translate schedule is enabled (operator step S4), run `translate drain --unit snapshot --max-tasks 5 --max-batches 1` once and record the 429 count and the released count. Record the Azure reset date (operator step S6) before the pacing is turned on.

## Commits

`test(ingest): define a rate-limited error for Azure throttling`, `feat(ingest): release rate-limited Azure work without an attempt`, `test(ingest): define chunk retries that do not re-bill`, `feat(ingest): retry Azure chunks without re-billing`, `feat(ingest): pace Azure characters per minute and per day`, `feat(scripts): measure translation-memory hit rate`.

## Out of scope

The translation memory table, the tier routing (chapter 7), and any change to the card unit or to the glossary modes.

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-azure-economy
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
