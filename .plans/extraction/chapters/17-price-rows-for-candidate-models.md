---
name: "Chapter E17 — Price rows for the candidate models"
overview: "Add verified price rows (and the request quirks the probe found) for the two candidates that have none, Mistral Small 3.1 24B and Llama 4 Scout 17B, so the eval and the drain can run them under the neuron guard."
todos:
  - id: prices
    content: "Price rows for mistral-small-3.1-24b-instruct and llama-4-scout-17b-16e-instruct, sourced and recorded"
    status: pending
  - id: probe
    content: "Envelope and payload checks against recorded probe shapes for both models"
    status: pending
isProject: false
---

# Chapter E17 — Price rows for the candidate models

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-candidate-prices` · **Status:** planned

**Depends on:** [E4](04-workers-ai-client-and-probe.md), [E5](05-eval-harness-and-model-choice.md), [E12](12-extraction-quality-tuning.md), [E14](14-raise-the-input-cap.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E16](16-documents-not-data-fields.md). Owner delegated the model choice (X16) to the chief of staff on 2026-10-29: test the candidates and choose by the rules in [gaps-and-decisions.md](../gaps-and-decisions.md). The model probe of 2026-10-28 showed `@cf/mistralai/mistral-small-3.1-24b-instruct` and `@cf/meta/llama-4-scout-17b-16e-instruct` grounding 6 of 7 and 6 of 7 items on the page where llama-3.3-70b corrupted umlauts, but neither has a row in `prices.py`, and the meter refuses an unpriced model (exit 2).

## Goal

Make both models runnable by `llm eval` and `worker drain` with the same neuron guard as the others, so the chief of staff can compare four models on the gold set.

## Contract

1. **Price rows.** `prices.py` gets one row per model: neurons per million input tokens and per million output tokens, taken from the Cloudflare Workers AI pricing page (`developers.cloudflare.com/workers-ai/platform/pricing/`, fetched with `curl`; if it cannot be fetched, derive the rate from the `usage.neurons` that a probe run reported for a known token count and say so in the return). The source and the date go in a comment beside the rows. The exact model ids are the ones the probe accepted (check the ids in the probe record and in the Cloudflare model catalogue).
2. **Reported neurons win.** Settlement already uses `usage.neurons` when present (E12); a row is needed only for the reservation and for models that do not report. A test shows the estimate for a recorded usage block is within 10 percent of the reported neurons.
3. **Request quirks.** If the recorded probe shows that either model needs a different payload field or an envelope shape that the current code does not read, add it behind the existing seams (`payloads.py`, `envelope.py`) with a recorded-shape test. If both already work, change nothing.
4. **No live call.** The chapter uses recorded shapes only. The chief of staff runs the live eval afterwards.

## TDD loops

### Loop A — Price rows

**Red** (`test_llm_prices.py`)

1. `both candidate models have a price row and are accepted by the meter`.
2. `estimate for a known usage block is within 10 percent of the neurons the API reported` (use the probe's recorded numbers: Mistral 105 neurons and Scout 97 neurons for the `aa-ferienbeschaeftigung` page; take token counts from the probe record, or from the eval cache if present).
3. `an unknown model id is still refused` (negative).
4. `reserved_output_tokens keeps the reservation of a 30,000-character page under the per-page maximum for both rows`.

**Green:** two rows and a source comment. **Refactor:** audit `prices.py` against the refactor gate (a table, not branching).

### Loop B — Envelope and payload (conditional)

**Red** (`test_llm_envelope.py`, `test_llm_payloads.py`): a recorded response of each model parses to the same `LlmResult`; a response with the answer as a string and as an object both parse. Build code only for a shape that fails.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest && ruff check . && mypy discovery_ingest
```

## Out of scope

Live model calls, choosing the model, editing the prompt, adding models beyond these two (`eurollm-9b-it` rejects `response_format`, `gemma-4-26b-a4b-it` timed out and are not candidates).
