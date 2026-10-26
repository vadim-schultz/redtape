---
name: "Chapter E4 — Workers AI client, neuron meter and probe"
overview: "An LlmClient port with an httpx adapter for Workers AI JSON mode, a neuron meter with reservation and reconciliation through the budget ledger, error classification, and a Step 0 probe that settles every response-shape and cost unknown before the handler depends on it."
todos:
  - id: probe
    content: "llm probe CLI and manual workflow that record shape, usage, accepted models, cost and quota behaviour"
    status: pending
  - id: client
    content: "LlmClient port and Cloudflare adapter"
    status: pending
  - id: meter
    content: "Neuron price table, estimate, reserve and adjust"
    status: pending
  - id: errors
    content: "Error classification mapped to release or fail"
    status: pending
isProject: false
---

# Chapter E4 — Workers AI client, neuron meter and probe

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/extraction-ai-client` · **Status:** planned

**Depends on:** crawlers [15](../../crawlers/chapters/15-cloudflare-render-and-snapshot.md) (stop reasons, release, throttle pattern), [23](../../crawlers/chapters/23-free-tier-guards.md) (ledger and `BudgetGuard`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

## Goal

Several facts about Workers AI are not in the documentation pages this plan was written from: the exact response envelope, whether token usage is returned, which models accept `response_format`, what a reasoning model really costs, and what the daily-limit error looks like. This chapter settles them with a probe first, then writes a small client that depends only on what the probe found. The free plan allows **10,000 neurons a day** and does not bill past it; a paid Workers plan would, so the budget code is a guard, not a formality (invariant 11).

## Step 0 — Probe (blocking, manual)

`python -m discovery_ingest llm probe --model <id> [--model <id>] --fixture <path>` (and the manual workflow `.github/workflows/discovery-llm-probe.yml`, `workflow_dispatch`, secrets `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_API_TOKEN`) sends the same cleaned fixture to each model and prints a table. Secrets are never printed. It must report, per model:

1. **Envelope:** the shape of the response to `POST /accounts/{id}/ai/run/<model>` with `response_format: {type: "json_schema", json_schema: ...}` (is `result.response` an object or a string?), and the same through the OpenAI-compatible `/ai/v1/chat/completions`, with which endpoint carries token usage.
2. **Usage:** whether input and output token counts come back, and whether reasoning tokens are counted separately.
3. **Acceptance:** whether the model accepts `response_format` at all (the documented list is `llama-3.3-70b-instruct-fp8-fast`, `llama-3.1-8b-instruct`, `llama-3-8b-instruct`, `hermes-2-pro-mistral-7b`, `deepseek-r1-distill-qwen-32b`; gpt-oss, gemma-4 and qwen3 variants are tested as candidates), and what happens when the schema is violated (the documented `JSON Mode couldn't be met` error, or an invalid body).
4. **Cost:** tokens in and out, computed neurons from the price table, and wall time, for the same page; the neuron counter in the Cloudflare dashboard is compared by the operator before and after the run.
5. **Quality sample:** the parsed `PageExtraction` and the grounded counts (chapter E3) so the eval has a first look.
6. **Quota:** the error body and status of a call after the daily allowance is used up. The probe does not try to provoke it; the first natural occurrence during chapter E5 or E7 is recorded in the ledger and the table below is finalised from it.
7. **Cleaner comparison:** characters and approximate tokens of the in-house cleaner (chapter E2) against Workers AI `toMarkdown` on the same snapshot, if `toMarkdown` accepts HTML; otherwise "not supported" is the finding.

The probe is the first commit of the chapter. `workflow_dispatch` only works once the file is on the default branch, so the first run is local with the two variables exported. Output, date and neurons used go in the ledger. Anything that contradicts the contract below changes the contract before the client is written.

## Contract

**Settings** (`IngestSettings`, all optional): `cloudflare_account_id`, `cloudflare_ai_api_token` (`CLOUDFLARE_AI_API_TOKEN`, a custom token with only the Workers AI permission the probe proves necessary), `llm_model` (default chosen in chapter E5), `llm_max_tokens` (1500), `llm_input_chars` (12000), `llm_request_timeout_seconds` (60). A drain of `llm_extract` requires the first two.

**Port** (`discovery_ingest/extract/llm/client.py`):

```text
class LlmClient(Protocol):
    def extract(self, messages: list[dict], json_schema: dict, *, max_tokens: int) -> LlmResult: ...
LlmResult: parsed_json: str, input_tokens: int | None, output_tokens: int | None, model: str
```

`CloudflareAiClient` is the only module that knows endpoint paths, the bearer token and the response envelope (as recorded by the probe). It uses `httpx` with the injected transport, sets `max_tokens` on every call, and raises the typed errors below.

**Neuron meter** (`meter.py`, pure plus the ledger calls):

- a price table keyed by model id with neurons per million input and output tokens (kept in one place; initial rows from Cloudflare's pricing page: llama-3.3-70b-instruct-fp8-fast 26,668 / 204,805; llama-3.1-8b-instruct 25,608 / 75,147; llama-3.1-8b-instruct-fp8-fast 4,119 / 34,868; gpt-oss-20b 18,182 / 27,273; gemma-4-26b-a4b 9,091 / 27,273; qwen3-30b-a3b 4,625 / 30,475); an unknown model is refused rather than guessed;
- `estimate(model, input_chars, max_tokens) -> int`: `ceil(input_chars / 3 × in_price / 1e6 + max_tokens × out_price / 1e6)` plus a small fixed overhead for the prompt text;
- `cost(model, input_tokens, output_tokens) -> float`;
- `NeuronMeter(guard)`: `reserve(model, input_chars, max_tokens)` calls the ledger (`neurons`) through `BudgetGuard.reserve`; a denial returns `Denied`, a ledger outage returns `LedgerUnavailable`; `settle(reservation, result)` calls `adjust` with `actual - reserved` when usage is present and leaves the reservation when it is not. A provider quota error calls `exhaust`.
- the run-level neuron budget (`--neuron-budget`, default 4000 so a live gate and a second run fit in the day) is the smaller of itself and the ledger's remaining neurons; without a reachable ledger the run budget alone applies and the report says `ledger_unavailable`.

**Error classification** (finalised from probe item 6; defaults):

| Response | Meaning |
| --- | --- |
| the daily allowance error (status and code from the probe) | `LlmQuotaExceeded`: mark the day exhausted, release, stop `llm_quota` |
| `401`, `403` | `LlmAuthError`: infrastructure; the run fails, tasks are released |
| `JSON Mode couldn't be met` or an unparseable body | `LlmInvalidOutput`: at most one repair retry (only if a second reservation is granted), then a permanent task failure noting the model |
| other `4xx` | permanent task failure |
| `429` without the quota code, `5xx`, timeout, connection error | retryable task failure |

An injected `Throttle` keeps a minimum interval between calls (default 1 s; Workers AI allows 300 text-generation requests a minute, so the neuron budget, not the rate, binds).

## TDD loops

All tests use `httpx.MockTransport`, a fake ledger client and an injected clock; nothing touches the network.

### Loop A — Client

**Red** (`apps/discovery-ingest/tests/test_llm_client.py`)

1. `extract posts the messages, schema and max_tokens with the bearer token and returns the json text and usage`.
2. `a missing usage block gives none tokens without raising`.
3. `the daily allowance error raises LlmQuotaExceeded; 401 and 403 raise LlmAuthError; the invalid-json error raises LlmInvalidOutput`.
4. `5xx, timeout and connection errors are retryable; other 4xx are permanent`.
5. `the token never appears in an exception message or log line`.

**Green:** one adapter module; endpoint paths in one table. **Refactor:** about a hundred lines.

### Loop B — Meter

**Red** (`test_neuron_meter.py`, `test_llm_budget.py`)

1. `estimate uses the model prices and grows with input and max_tokens`.
2. `an unknown model is refused`.
3. `reserve is granted within the ledger and denied beyond it, and the run budget caps both`.
4. `settle adjusts by actual minus reserved, and keeps the reservation when usage is missing`.
5. `a quota error exhausts the day in the ledger`.
6. `an unreachable ledger falls back to the run budget and reports ledger_unavailable`.

**Green:** meter built on `BudgetGuard`. **Refactor:** prices and the formula live in one module.

### Loop C — Probe

**Red** (`test_llm_probe.py`)

1. `the probe prints a table per model and never prints the token`.
2. `the probe exits non-zero when settings are missing`.
3. `the probe reports an unsupported response_format as a finding instead of crashing`.

**Green:** CLI function over the client. **Refactor:** each probe item is a function returning a result row. The workflow file passes the existing workflow lint.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_llm_client.py tests/test_neuron_meter.py tests/test_llm_budget.py tests/test_llm_probe.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate (needs crawlers operator steps S15–S21 and extraction step X1 of [E9](09-docs-and-operator-steps.md)):

```bash
python -m discovery_ingest llm probe --model @cf/meta/llama-3.3-70b-instruct-fp8-fast --model @cf/meta/llama-3.1-8b-instruct --model @cf/openai/gpt-oss-20b --fixture tests/fixtures/pages/<page>.html
```

Record the table, the neurons shown in the Cloudflare dashboard before and after, and the date in the ledger, then finalise the error table. Keep it to a few calls: the whole probe should cost well under 1,000 neurons.

## Out of scope

Choosing the model (chapter E5), the handler (E6), streaming, embeddings, batching several pages in one call, any other provider (a future adapter behind the same port).
