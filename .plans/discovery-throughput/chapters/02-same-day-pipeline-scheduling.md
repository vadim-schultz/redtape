---
name: "Chapter 2 — Same-day pipeline scheduling"
overview: "Split extract_page and capture_screenshot into their own workflows and retime all five stages so every pipeline hop completes the same calendar day."
todos:
  - id: drain
    content: "Trim discovery-drain.yml to fetch_url,enrich_metadata,harvest_payload at 02:00"
    status: pending
  - id: render
    content: "Trim discovery-render.yml to render_page at 03:00; wire LLM_ENQUEUE and LLM_MODEL"
    status: pending
  - id: extract
    content: "Create discovery-extract.yml for extract_page at 04:00"
    status: pending
  - id: llm
    content: "Retime discovery-llm.yml to 04:30"
    status: pending
  - id: screenshot
    content: "Create discovery-screenshot.yml for capture_screenshot at 05:00"
    status: pending
  - id: concurrency
    content: "Rename the shared concurrency group to discovery-pipeline everywhere"
    status: pending
isProject: false
---

# Chapter 2 — Same-day pipeline scheduling

**Repo:** `redtape` (`.github/workflows`) · **Branch:** `feat/discovery-throughput-same-day-pipeline` · **Status:** planned

**Depends on:** none · **Decisions:** D7, D8, D9 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-throughput`

## Goal

Reorder and split the five discovery workflows so every pipeline hop's consumer runs after its producer, on the same calendar day — eliminating the ~2-day latency described in [00-architecture.md §1](../00-architecture.md). No CLI or worker code change is needed; `--kinds` is already a free-form comma-separated list on every drain workflow (D7).

## Design

- [`discovery-drain.yml`](../../../.github/workflows/discovery-drain.yml): cron `0 2 * * *` (was `0 4 * * *`); `kinds` default and `workflow_dispatch` input default → `fetch_url,enrich_metadata,harvest_payload` (drop `extract_page`); `timeout-minutes: 30` (was 45, one fewer kind). Gate var stays `DISCOVERY_DRAIN_SCHEDULE`.
- [`discovery-render.yml`](../../../.github/workflows/discovery-render.yml): cron `0 3 * * *` (was `0 5 * * *`); `kinds` default → `render_page` (drop `capture_screenshot`); `timeout-minutes: 20` (was 30). **Add to the job `env`** (ties to D8): `LLM_ENQUEUE: "true"` and `LLM_MODEL: ${{ vars.DISCOVERY_LLM_MODEL }}` — required together, because `prepare_llm_enqueue` (`apps/discovery-ingest/discovery_ingest/worker/llm_setup.py:86-100`) raises `LlmSetupError` if `LLM_ENQUEUE` is on without `LLM_MODEL` set. Gate var stays `DISCOVERY_RENDER_SCHEDULE`.
- **New** `discovery-extract.yml`: same structure as the current `discovery-drain.yml` (checkout, setup-python with pip cache, Actions-minutes budget check, wait-for-health, drain, job-summary, minutes-report), `kinds: extract_page`, cron `0 4 * * *`, `timeout-minutes: 20`, new gate var `DISCOVERY_EXTRACT_SCHEDULE`, same concurrency group.
- [`discovery-llm.yml`](../../../.github/workflows/discovery-llm.yml): cron `30 4 * * *` (was `0 6 * * *`); everything else unchanged; gate var stays `DISCOVERY_LLM_SCHEDULE`.
- **New** `discovery-screenshot.yml`: same structure as the current `discovery-render.yml` (Cloudflare Browser Rendering secrets, `browser_seconds` budget guard), `kinds: capture_screenshot`, cron `0 5 * * *`, `timeout-minutes: 20`, new gate var `DISCOVERY_SCREENSHOT_SCHEDULE`, same concurrency group.
- Rename `concurrency.group` from `discovery-drain` to `discovery-pipeline` across all five workflow files plus `platform-maintenance.yml`'s `discovery` job (D9) — purely cosmetic now that it spans five scheduled files, not two.
- `apps/discovery-ingest/discovery_ingest/schemas.py` — leave `WORKER_DEFAULT_TASK_KINDS` (the CLI's own `--kinds` default for a human who omits the flag entirely) unchanged; it is a laptop-run convenience, not a scheduling concern.

## Tests

There is no workflow-YAML test harness in this repo (confirmed: no `act`, no `actionlint` step in any existing workflow). The red/green for this chapter is:

- Red: `python -c "import yaml, sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/discovery-*.yml` fails until the two new files exist and every file parses.
- Green: all five files exist and parse.
- If `actionlint` is available via `docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest` (the pattern used in `.plans/gha-budget/01-rollout.md`), run it; otherwise rely on manual review plus the live gate below.
- `docs/operations/scheduled-jobs.md` (updated in chapter 5) is the regression check that the written schedule matches the shipped YAML.

## Verification

Live gate, after merge to `main` (scheduled workflows only fire from the default branch):

```bash
gh workflow run discovery-drain.yml -f max_batches=1
gh workflow run discovery-render.yml -f max_batches=1
gh workflow run discovery-extract.yml -f max_batches=1
gh workflow run discovery-llm.yml -f max_batches=1
gh workflow run discovery-screenshot.yml -f max_batches=1
gh run list --workflow=discovery-screenshot.yml --limit 1 --json conclusion,createdAt
```

After one full day with all schedules enabled (chapter 6), confirm a page fetched that morning reaches `capture_screenshot` the same day.

## Refactor gate

YAML only — no code to refactor. If the two new files duplicate too much of the existing files' steps, record that as a deferred seam ("extract a reusable composite action") rather than doing it in this chapter; scope here is schedule correctness, not DRY-ing workflow YAML.

## Commits

- `feat(workflows): split extract_page and capture_screenshot into dedicated schedules`
- `fix(workflows): reorder the discovery cron pipeline to complete same day`

## Out of scope

Turning any new gate variable to `enabled` (chapter 6); any CLI/worker code change (none needed per D7).
