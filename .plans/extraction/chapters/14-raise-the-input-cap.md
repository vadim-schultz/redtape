---
name: "Chapter E14 — Raise the input cap"
overview: "Raise the cleaned-text cap from 12,000 to 30,000 characters and the output limit with it, so long procedure pages reach the model whole. Quality over throughput: the bulk import happens once and refreshes are occasional."
todos:
  - id: cap
    content: "Cleaner, settings and handler defaults at 30,000 characters; CLEAN_VERSION clean-3"
    status: pending
  - id: output
    content: "Output limit raised so a long page's answer is not truncated; reservations stay honest"
    status: pending
  - id: docs
    content: "README, runbooks and the extraction plan numbers say the same values"
    status: pending
isProject: false
---

# Chapter E14 — Raise the input cap

**Repo:** `redtape` (`apps/discovery-ingest`, docs) · **Branch:** `feat/extraction-input-cap` · **Status:** planned

**Depends on:** [E2](02-page-cleaner.md), [E4](04-workers-ai-client-and-probe.md), [E12](12-extraction-quality-tuning.md), [E13](13-grounding-normalisation.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E13](13-grounding-normalisation.md) and before [E7](07-wiring-and-workflow.md).

## Goal

Owner decision (2026-10-28): the bulk of the pages is imported once and then refreshed occasionally, so pages per day matters less than extraction quality. The cap of 12,000 characters was set to keep a page near 4,000 tokens. On the 77 real pages with text, 35 (45 percent) exceed it, and the cap cuts document lists at the end of long procedure pages (page text up to 44,400 characters; median 6,028, p90 21,433). At 30,000 characters only 4 pages remain over the cap. The model's context window (about 24,000 tokens for `@cf/meta/llama-3.3-70b-instruct-fp8-fast`) holds 30,000 German characters (about 10,000 tokens) with room for the prompt and the answer.

Cost, stated plainly: a long page costs about 270 input neurons instead of 110, and a long answer up to about 800 output neurons; the daily allowance (9,500 neurons) then covers roughly 30 to 60 pages a day, and the pages with short text cost what they cost today. That is accepted.

## Contract

1. **One number.** `DEFAULT_MAX_CHARS` in the cleaner, `LLM_INPUT_CHARS` (`llm_input_chars` in `LlmSettings`) and the handler's `max_chars` default become **30,000**, defined once and imported by the other two. `CLEAN_VERSION` becomes `clean-3`, so cached eval answers and `extractor_version` change with it (`extractor_version()` stays within 32 characters).
2. **Output limit.** `LLM_MAX_TOKENS` (default 1,500 today) becomes **4,000**, enough for a page that lists the documented maximum of documents and dependencies in the schema (`MAX_DOCUMENTS` and `MAX_DEPENDENCIES` are 40) with ordinary-length quotes; a test pins that a worst-case realistic answer fits. A model answer cut by the limit stays an `LlmInvalidOutput` (repair path of E6), not a silent loss.
3. **Reservations stay honest.** `estimate` uses the new defaults, so one reservation is larger (about 1,100 neurons at the maximum); the eval and drain run budgets keep working as upper bounds. Check and fix the "stops before a page that would pass the budget" behaviour of the eval and the drain so the default budgets still process several long pages (the eval default of 4,000 stops early with 1,100-neuron reservations; report what you chose, for example reserving the estimate from the page's actual length instead of the maximum).
4. **Ordering under the cap is unchanged** (E12): main content first, menu-like blocks last.
5. **Pages over the cap** (about 5 percent) are still truncated by whole lines, `truncated=True`; splitting a page over several model calls is out of scope.
6. **Docs.** The README, the runbooks, the architecture and the rollout say 30,000 and 4,000 where they say 12,000 and 1,500 today.

## TDD loops

### Loop A — One cap

**Red** (`test_clean_page_cap.py`, `test_llm_settings.py`, `test_llm_extract_worker.py`)

1. `the cleaner, the settings and the handler share one cap of 30,000 characters`.
2. `a 25,000-character page is not truncated and a 35,000-character page is truncated with truncated=True` (negative).
3. `CLEAN_VERSION is clean-3 and extractor_version stays within 32 characters`.
4. `cleaner_recall on the gold set with the default cap is 47 of 47` (the E12 run left 46 of 47; update the pinned number in the eval command test and the gold manifest hashes only for pages whose cleaned text changes).

**Green:** one constant, imported twice. **Refactor:** the cap lives in one module.

### Loop B — Output limit and reservations

**Red** (`test_llm_settings.py`, `test_neuron_meter.py`, `test_llm_eval_command.py`, `test_llm_extract_stops.py`)

1. `the default output limit is 4,000 tokens and a worst-case realistic answer fits`.
2. `the estimate for a 30,000-character page with the new limit is below the daily cap and is an upper bound of the recorded cost` (use the recorded probe: 1,597 prompt and 574 completion tokens cost 160.1 neurons).
3. `an eval run with the default budget processes at least five long pages before it stops for the budget` (negative of the early stop; fake client).

**Green/Refactor:** one small change at the reservation site; audit `meter.py` and the eval runner against the refactor gate.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest && ruff check . && mypy discovery_ingest
```

Offline measurement for the return: over the 77 real pages (the pool at `.../scratchpad/pool`, read-only) the cleaned length distribution, how many are truncated at the new cap, and the estimated neurons per page at the new defaults. No model calls. The chief of staff re-runs the live eval afterwards.

## Out of scope

Splitting long pages over several calls, changing the model, the prompt or the gold labels, raising the free-tier caps.
