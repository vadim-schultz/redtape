# C4 — Local LLM extraction

**Depends on:** C0 · **Batch:** 2 · **Branch:** `feat/local-queue-drain-llm`

## Goal

Drain `llm_extract` tasks on this machine with a local Qwen model served by llama.cpp's OpenAI-compatible server, at a throughput that matters, and with extraction quality that matches the Workers AI run on a labelled sample.

## Measurement gate first (no code)

The P2000 is not usable until the machine reboots (O1), so the first measurement is CPU only.

1. Build llama.cpp from source in the scratchpad: `cmake` and `ninja` from PyPI, the CPU build with AVX2 enabled (the default on this CPU). Record the commit.
2. Download the 4-bit K-quant GGUF builds of `Qwen3.8-27B` (dense) and `Qwen3.6-35B-A3B` (mixture of experts, about 3B active) from the official `ggml-org` organisation on Hugging Face (`ggml-org/Qwen3.8-27B-GGUF` and `ggml-org/Qwen3.6-35B-A3B-GGUF`) into the scratchpad. Record each file's size. Do not put weights in the repo.
3. Run `llama-bench` with `-t` set to the physical core count (28), `-p 2048` for prompt processing and `-n 256` for generation. Record prompt tokens per second and generation tokens per second for each model. The dense 27B model reads all its weights for every token, so expect it to be the slower of the two.
4. Compute the target. A page's cleaned input is about `DEFAULT_MAX_CHARS` characters (`extract/clean.py`); the output is a JSON answer of a few hundred tokens. Pages per hour = 3600 / (prefill time for the input + generation time for the output), with the server running `-np` parallel slots. Gate: at least 300 pages per hour for the whole machine, which is more than the Workers AI run completes in a day. If neither model reaches it, the stage stops and the ledger records the numbers.
5. Quality gate: run the labelled sample used by `extract/llm/evaluation` through the local model and through Workers AI. Gate: JSON validity ≥ the Workers AI run, and the grounded-mention agreement within the threshold the evaluation harness already defines.

## Slices (red → green → refactor each)

### Slice 4a — client

- **Happy:** `LocalChatClient.extract(messages, schema, max_tokens=...)` against a fake llama-server returns an `LlmResult` whose `parsed_json` parses against the schema, with `model` equal to the configured local model string and `neurons` `None`.
- **Negative:** a 500 from the server raises `LlmRequestError` with `retryable=True`. A body that is not JSON raises `LlmInvalidOutput`, which the caller repairs once (existing `ModelCaller` behaviour).

### Slice 4b — setup and meter

- **Happy:** `prepare_llm` with the local provider and a model string that has no neuron price returns resources, and the drain reserves nothing from the neuron ledger (I2). The price check in `_check_settings` is skipped for the local provider only.
- **Negative:** `prepare_llm` with the local provider and no model string raises `LlmSetupError` with exit code 2, as the Workers AI path does for a missing model.

### Slice 4c — policy

- **Happy:** a `DrainPolicy` for `llm_extract` with the local provider builds without a neuron budget, because the local path has no neuron budget to enforce.
- **Negative:** the same policy with the Workers AI provider still raises `ValueError` when `neuron_budget` is missing (the existing rule holds for the remote path).

## Green

- Implement `LocalChatClient` behind `LlmClient`, against the llama.cpp `/v1/chat/completions` endpoint with a JSON schema constraint. Reuse the message builder and the schema from `extract/llm/prompt.py` and `schema.py`.
- Add a `--provider local` switch and a local model string (a setting, not a Workers AI price).
- Each claim takes one task (`limit=1`, D11). The run report records the local model string (D12).
- Keep `CloudflareAiClient` as it is.

## Refactor

- `build_model_client` (`operations/models.py`) builds only the Workers AI client. With two providers, a factory per provider is the answer: `_client_for(provider)`.
- The neuron meter and the local no-meter path share a reservation call. Give the local path a no-op meter with the same interface, so `ModelCaller` does not branch.
- `llm_setup._check_settings` has four early exits. Extract the provider-specific checks into two functions and call one of them.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "llm and local" -q
cd apps/discovery-ingest && .venv/bin/python -m ruff check discovery_ingest && .venv/bin/python -m mypy discovery_ingest
```

Then `llama-bench` and the labelled-sample comparison, recorded in the ledger.

## Exit

- The throughput target and the quality gate are both recorded with their commands. O3 closed with the chosen model.
- The run report carries the local model string. The server stores no model on LLM results (D12), so the report is the only record.
- One bounded local LLM drain completes against the live queue. The neuron counter does not move because of local work.
