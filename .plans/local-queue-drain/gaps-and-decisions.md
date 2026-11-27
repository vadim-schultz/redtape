---
name: Local queue drain — Gaps and decisions
overview: "Settled decisions from the audit and the operator's answers, and open questions with their defaults, for running discovery workers locally and on hosted runners."
isProject: false
---

# Local queue drain — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Decided

| ID | Decision | Reason | Chapters affected |
| --- | --- | --- | --- |
| D1 | GitHub Actions minutes are not a constraint. The minute cap, the 2,000/1,000/1,000 split and the minute prechecks are obsolete. | The repository is public, so hosted minutes are unmetered (pipeline-optimisation D17, 2026-11-23). The operator confirmed it on 2026-11-27. | C0 |
| D2 | No GitHub self-hosted runner is registered on this public repository. | Fork pull requests could run code on the machine, and runners keep state between jobs. Zero runners are registered today. | C5 |
| D3 | Local workers are a daemon that calls the existing CLI, with a dedicated machine key. They are not GitHub runners. | Keeps the queue contract and the reports, with no runner registration and no new trust path. | C5 |
| D4 | Local work never reserves in the Cloudflare or Azure ledger. The local worker keeps its own run budget and reports its own spend. | Ledger headroom belongs to the remote workers. A local reservation would starve them. | C1–C4 |
| D5 | A local embedding model is used only for the model string whose weights it reproduces. Its vectors are written only after the parity gate passes. | Search reads vectors by model string, and query-time embedding stays on Workers AI. A different model would silently mix vector spaces. | C1 |
| D6 | Each local run has a time budget below one hour. | Starting a run closes every run still `running` after one hour. | C5 |
| D7 | Translation first pass: a local engine takes a lane of its own, and Azure's upgrade path stays as it is. | The upgrade path already exists (`UPGRADE_BASE`). Azure's monthly characters then go to upgrades, not first passes. | C3 |
| D8 | The browser stays behind the existing `BrowserClient` port. The Playwright adapter mirrors the Cloudflare request shape: `networkidle2`-style navigation with a 30 s timeout, 1280×800, full-page JPEG at quality 80, the consent CSS and the consent script. | One port, one behaviour, and the probe can compare them. | C2 |
| D9 | The docs this plan finds stale are fixed in C0, not in the feature chapters. | Each chapter then starts from the true budget picture. | C0 |
| D10 | Local workers only drain. They claim a task, work it and settle it; they never create tasks ahead of a claim. The effects that completing a task already has on the pipeline still happen on whichever worker completes it. A render's completion creates the `extract_page` and `llm_extract` tasks, as the GHA render does; without them, pages rendered locally would never reach extraction. The screenshot sweep runs before the claim and queues `capture_screenshot` tasks, so local workers turn it off (`screenshot_sweep_limit=None`, not the setting's default of 50). | Operator, 2026-11-27: local workers shouldn't initiate anything. Read of the code: the sweep initiates work; the render completion hooks settle it. | C2, C4, C5 |
| D11 | Every local claim takes one task (`limit=1`). | Operator, 2026-11-27: drain one task at a time. The cost, one text per forward pass for embedding, is measured in C1. | C1–C5 |
| D12 | The LLM task key stays as the enqueuer set it (`LLM_MODEL`, at render completion). Local workers do not change it. The server stores no model on LLM results: the only `model` field in `schemas.py` is on snapshot completions. A local LLM run records its model string in its run report. | Closes former O4. Local workers consume tasks, so they have no key to choose. | C4 |
| D13 | Object storage is not a constraint of local work. The 9.5 GB cap, the R2 operations and the stored bytes are out of this plan. | Operator, 2026-11-27: a single source of truth with a limit so high it does not matter, and not something to replace. Closes former O7. | C0, C2 |
| D14 | Qwen4-Max is not a candidate for now. Its blog page is JavaScript-only: the raw HTML holds no article text. The Hugging Face Qwen organisation has no Qwen4 repository, and Qwen3.8 is the newest family there (operator, 2026-11-27). The "Max" tier was API-only in earlier Qwen releases (background knowledge, not verified here). | The page could not be read, so its licence and weights status are unknown. Revisit when weights appear on Hugging Face or ModelScope. | C4 |
| D15 | The operator creates the machine key for local workers; C0 records its name only. | Operator confirmed, 2026-11-27. Closes former O9. | C0 |
| D16 | The project is non-commercial, so NLLB-200 distilled 600M (CC-BY-NC-4.0) and Tower-Plus-9B (CC-BY-NC-SA-4.0) are eligible alongside MADLAD-400-3B-MT and Opus-MT. | Operator, 2026-11-27. The non-commercial licences restrict commercial use only. | C3 |

## Open

| ID | Question | Default if no answer | Forcing condition |
| --- | --- | --- | --- |
| O1 | GPU. The driver is installed (`nvidia-driver-580`, module signed by Canonical, Secure Boot off). The P2000 is bound to the open `nouveau` driver, and `/dev/nvidia*` does not exist. The blacklist in `/lib/modprobe.d/nvidia-graphics-drivers.conf` takes effect at boot, so a reboot is needed. Whether CUDA runs on this Pascal card (sm_61) with driver 580 is not verified. | CPU-only until the operator reboots and `nvidia-smi` lists the P2000. C1–C3 do not need the GPU. | Operator reboot; C4 gate. |
| O2 | Translation engine for the local first pass. All four candidates are eligible (D16): MADLAD-400-3B-MT, Opus-MT (de-en, de-pl and de-uk on the Hub; the de-tr, de-ru and de-ro names were not found), NLLB-200 distilled 600M and Tower-Plus-9B. | Benchmark all four in C3 on the German sample. Each locale is served by the engine that passes its gate and scores best. | C3 benchmark. |
| O3 | Which LLM for C4. Qwen3.8-27B is the newest: a dense 27.8B model under Apache-2.0 with official GGUF builds (`ggml-org/Qwen3.8-27B-GGUF`). A dense model reads all its weights for every token, so CPU throughput is the likely limit. Qwen3.6-35B-A3B (mixture of experts, about 3B active, Apache-2.0, `ggml-org/Qwen3.6-35B-A3B-GGUF`) is an earlier generation that suits CPU decoding. Qwen3.8-Flash-Next is 180B under a custom licence and is out. | Benchmark both with `llama-bench` in C4. Choose the newest model that passes the throughput gate, then the quality gate. | C4 gate. |
| O5 | Stock Playwright, or Patchright for the anti-bot targets? | Stock Playwright, with the probe showing whether the canary pages block it. Switch only on evidence. | C2 probe. |
| O6 | Keep the `actions_minutes` resource and its config, or remove them? | Keep them, marked obsolete, until a separate chapter removes the enum values. Removal changes API contracts. | C0. |
| O8 | Hosted runners for browser work (a matrix of free public-repo jobs)? Their concurrency cap and per-job limits are not verified. | Not planned now. Revisit after C2, once a concurrency figure is verified in GitHub's documentation. | C2 gate passes and the local browser is not enough. |

## Measured on this machine (2026-11-27)

- CPU: 56 logical CPUs, Xeon E5-2690 v4, AVX2/FMA/F16C/BMI2, no AVX-512.
- RAM: 503 GiB. Free disk on `/`: 176 GB.
- GPU: P2000 on the PCI bus. Driver 580 installed, bound to `nouveau`, not usable until a reboot (O1).
- Docker works without sudo.
- Reachable: pypi.org, huggingface.co, github.com, registry.npmjs.org, ollama.com, the Cloudflare API and Azure's translator endpoint.
- Not measured yet: llama.cpp throughput, Playwright per-page cost, embedding throughput, translation quality. Each gate measures one of these.
