---
name: "Chapter E7 — Wiring and workflow"
overview: "Enqueue llm_extract after every rendered snapshot, trigger screenshots for pages with mentions, add the requeue command for new prompt versions and for the existing backlog, and a bounded workflow that skips itself when a budget is gone."
todos:
  - id: enqueue
    content: "after_snapshot enqueues llm_extract with a versioned input key, behind a switch"
    status: pending
  - id: screenshot
    content: "Screenshot helper wired into the handler"
    status: pending
  - id: requeue
    content: "llm requeue command for the backlog and for version bumps"
    status: pending
  - id: workflow
    content: "discovery-llm.yml with budget skip, minutes report and a schedule gated by a variable"
    status: pending
  - id: live
    content: "Live run from real snapshots, recorded"
    status: pending
isProject: false
---

# Chapter E7 — Wiring and workflow

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/extraction-wiring` · **Status:** planned

**Depends on:** [E6](06-llm-extract-handler.md), and crawlers [15](../../crawlers/chapters/15-cloudflare-render-and-snapshot.md), [17](../../crawlers/chapters/17-extractor-framework.md), [19](../../crawlers/chapters/19-screenshot-capture.md), [23](../../crawlers/chapters/23-free-tier-guards.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

## Goal

Make extraction happen by itself for new snapshots and on demand for existing ones, inside the free budgets, with the screenshot evidence following only for pages that produced mentions.

## Contract

**Enqueue.** The `after_snapshot` hook of crawlers chapter 15 and 17 gains a second action: when `llm_enqueue` is true (a worker setting, default **false** until chapter E5's decision is recorded, so no neurons are committed by accident) it enqueues `llm_extract` through `POST /machine/tasks` with `artifact_id`, `target_url = artifact.source_url`, priority 200 and `input_key = "llm:" + hash8(model | PROMPT_VERSION | clean version)`. Identity dedupes it, so re-rendering a page does not create a second open task for the same version; a new snapshot (new `artifact_id`) is a new task by design. An enqueue error is logged and counted (`llm_enqueue_failed`); the render task still completes.

**Screenshot.** `handle_llm_extract`'s `after` callable is the shared helper of crawlers chapter 19 (`enqueue_screenshot_for_mentions`): one `capture_screenshot` per page, only after at least one mention was posted, `input_key = "shot@1"`, priority 300.

**Requeue.** `python -m discovery_ingest llm requeue [--host H] [--limit N] [--dry-run]` lists the latest `html_snapshot` per catalogue row (machine artifacts list route, crawlers chapter 14), skips pages that already have a task for the **current** key, and enqueues `llm_extract` for the rest. `--limit` defaults to 50 and refuses more than 200 before any call. This is how the existing backlog is processed after deploy and how a prompt, model or cleaner bump re-runs pages (decision X13). It prints counts only.

**Workflow** `.github/workflows/discovery-llm.yml`:

- `workflow_dispatch` inputs `max_tasks` (5), `max_batches` (20), `time_budget_seconds` (600), `neuron_budget` (4000) and `kinds` (`llm_extract`); a daily schedule (06:00 UTC) gated by the repository variable `DISCOVERY_LLM_SCHEDULE == 'enabled'`, off by default.
- Secrets: `DISCOVERY_API_URL`, `DISCOVERY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN`. Same shape as `discovery-drain.yml` (health wait, report to the job summary, fail the job when `succeeded` is false), the **same `concurrency` group** `discovery-drain`, `timeout-minutes: 20`, installs the ingest package only (no extra: the cleaner and client need no new dependency).
- First step: `python -m discovery_ingest budget show --require-remaining actions_minutes=20 --require-remaining neurons=300` and skip when it exits 3. Last step (`if: always()`): report the job minutes to the ledger (crawlers chapter 23).
- A run that stops on `llm_budget`, `llm_quota`, `db_limit`, `time_budget`, `batch_limit` or `queue_empty` succeeds; only infrastructure errors fail the job.

**Cost.** Neurons, not time, bind: a 600-second run at the measured neurons per page (chapter E5) processes whatever the 4,000-neuron run budget allows, probably under 40 pages. The backlog should mostly run **locally** (no Actions minutes), at most one run a day, with the workflow as a top-up while this repository's 1,000-minute cap has room (crawlers chapter 23):

```bash
python -m discovery_ingest worker drain --kinds llm_extract --max-tasks 5 --max-batches 20 \
  --time-budget-seconds 600 --neuron-budget 4000
```

## TDD loops

### Loop A — Enqueue and screenshot

**Red** (`apps/discovery-ingest/tests/test_llm_wiring.py`)

1. `after_snapshot enqueues llm_extract with the artifact id and a versioned key when llm_enqueue is on, and not when it is off`.
2. `the same version does not create a second task for the same artifact; a bumped prompt version does`.
3. `an enqueue error is counted and does not fail the render`.
4. `llm_extract enqueues one capture_screenshot when mentions were posted and none otherwise` — through the shared helper.

**Green/Refactor:** pass the callables at construction, like the extractor hook.

### Loop B — Requeue

**Red** (`test_llm_requeue.py`)

1. `requeue enqueues one task per latest snapshot without a current-key task`.
2. `requeue skips pages that already have the current key and enqueues again after a version bump`.
3. `requeue --dry-run makes no enqueue call; a limit over 200 is rejected before any call`.
4. `requeue prints counts only and never the token`.

**Green:** CLI function over the client. **Refactor:** selection separate from enqueueing.

### Loop C — Workflow

**Red** (`test_discovery_llm_workflow.py`)

1. `discovery-llm.yml has timeout-minutes, the budget skip step, the always-run minutes step, the shared concurrency group and a schedule gated by DISCOVERY_LLM_SCHEDULE`.
2. `the workflow passes only the four named secrets and installs no extra`.

**Green:** the workflow file. **Refactor:** none; the existing workflow lint also runs in CI.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_llm_wiring.py tests/test_llm_requeue.py tests/test_discovery_llm_workflow.py tests/test_llm_extract_worker.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate (needs [E9](09-docs-and-operator-steps.md) steps X1–X7 and crawlers S15–S21; spends neurons, plan it for one day):

```bash
python -m discovery_ingest llm requeue --limit 20
gh workflow run discovery-llm.yml -f max_tasks=5 -f max_batches=4 -f neuron_budget=2500   # or the local command above
gh run view --log        # neurons_used, llm_calls, released, stop_reason
```

Then open `GET /api/v1/discovery/admin/candidates?` and a candidate detail: mentions with `extractor = llm`, roles including `issued`, conditions, suggested tags, edges. Read ten mentions against their source pages and record the precision observed (for example "8 of 10 real"), the neurons used per page, the ledger's `neurons` figure, and the run ID. Confirm at least one `capture_screenshot` task was enqueued for a page with mentions and none for a page without.

## Out of scope

Enabling the schedule (operator step X9, after the live gate), the admin display (E8), automatic emit, backfilling snapshots that do not exist yet (crawlers operator step S14).
