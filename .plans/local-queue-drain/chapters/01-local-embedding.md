# C1 — Local embedding

**Depends on:** C0 · **Batch:** 1 · **Branch:** `feat/local-queue-drain-embedding`

## Goal

Drain `embedding_task` rows on this machine with Qwen3-Embedding-0.6B, on the local GPU when its parity gate passes and on CPU otherwise, writing vectors that search can use, and only after proving they match Workers AI.

## Measurement gate first (no code)

The Workers AI model is `@cf/qwen/qwen3-embedding-0.6b` (`llm_settings.py`). That the hosted weights equal the Hugging Face `Qwen/Qwen3-Embedding-0.6B` is not verified here. The parity probe settles it.

1. Download `Qwen/Qwen3-Embedding-0.6B` with `huggingface_hub` into the scratchpad, not the repo.
2. Embed 50 texts drawn from stored candidate text. Use the raw text, no instruction prefix, as the worker does (`EmbeddingClaimResponse` says "raw, no instruction prefix").
3. Call the Workers AI model on the same 50 texts through `CloudflareEmbeddingClient`, using `embed_body` and `read_embeddings`.
4. Compare per text: cosine similarity, vector length (must be 1024, `EMBEDDING_DIM`), and the norm. Run the probe on CPU and on the GPU, in the runtime that would serve it. A GPU runtime must be a CUDA 12.x build, because CUDA 13 has no offline compilation for Pascal (D28). The probe records the device, the runtime version and the peak VRAM.
5. Gate: every cosine ≥ 0.999 and every length 1024, on at least one device. The device that passes and is faster serves the work. If neither device passes, the chapter stops: no adapter is written, and the ledger records the cosine range. Pooling or normalisation differences show up here first.

The probe is a script in `apps/discovery-ingest/discovery_ingest/extract/embedding/probe_local.py` if it passes. Its output is a parity record (`model`, `weights_revision`, `device`, `cosine_min`, `sample_size`, `date`) committed under `docs/operations/` or the run ledger.

## Slices (red → green → refactor each)

### Slice 1a — parity comparison

- **Happy:** `compare_parity(local, remote, threshold=0.999)` returns `ParityResult(ok=True)` for 50 identical vectors.
- **Negative:** the same call with one vector scaled to a different direction returns `ok=False` and names the failing index. It does not raise, and it does not pass silently.

### Slice 1b — local embedder

- **Happy:** `LocalQwenEmbedder.embed(["Mietvertrag"])` returns an `EmbeddingResult` with one vector of length 1024, L2-normalised within 1e-5, and `model` equal to the configured string.
- **Negative:** `embed([])` raises `ValueError` naming the empty input. A text longer than the model's context is truncated and the result says so; it does not raise a shape error.

### Slice 1c — drain gate and budget

- **Happy:** `run_embed_drain` with the local embedder, a local budget API (grants all, reserves nothing) and a stub machine client completes one batch: `completed_count` equals the claim size, and the ledger reservation count is zero (I2).
- **Negative:** with no parity record on disk, the drain refuses to start and returns an error report before claiming anything (I3). The claim count is zero.

## Green

- Implement the parity comparison, the local embedder behind the `Embedder` protocol, and the local budget API in a new module (`budget_local.py`). Add the `--provider local` switch to the embed CLI.
- Each claim takes one task (`limit=1`, D11). The `embed` type has one slot, so one claim loop runs (C5). The parity run records the throughput cost of one text per forward pass in the ledger. On the GPU, the embedder's VRAM stays within the type's 1536 MiB.
- Keep the query path on Workers AI. Do not change `cloudflare_embedder.py`.

## Refactor

- `embed_drain._open_meter` chooses a meter by provider. With two providers, a factory per provider is cheaper than a branch. Extract `_meter_for(provider)` with one function per provider.
- The parity record and the embedder share the model string constant. Move it to one place, `llm_settings.py`, and import it.
- Check `extract/embedding/client.py` for the total number of branches on the provider, not only the ones this chapter adds.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "embed or parity" -q
cd apps/discovery-ingest && .venv/bin/python -m ruff check discovery_ingest && .venv/bin/python -m mypy discovery_ingest
```

Then the parity probe on the real sample (not in CI): the cosine range and the top-10 agreement for 20 queries against Workers AI are recorded in the ledger.

## Exit

- Parity gate passed and recorded.
- One local embed drain completes against the live queue in a bounded run, with its report in the ledger and no ledger reservation.
- The search top-10 agreement for 20 queries is at least 18 of 20. Anything lower stops the stage.
