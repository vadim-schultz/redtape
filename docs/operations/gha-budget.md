# GitHub Actions budget and operator checklist

This repository is public. GitHub does not meter Actions minutes on standard runners of a public repository, so no minute
cap binds (pipeline-optimisation decision D17). The limits that bind are Cloudflare browser seconds, Workers AI neurons,
Azure characters, and R2 and database size. This page keeps the October and November minute records and the steps that
still apply. Workflow behaviour and the budget ledger are in [scheduled-jobs.md](scheduled-jobs.md).

## What happened in October (history)

The account reached its Free-plan pool early. This repository used 960 of the minutes; the other repositories used about
1,040. When the pool is gone, every job fails in about 3 seconds with a billing error.

| Workflow | Min (October) | Runs | Cause |
| --- | --- | --- | --- |
| `openplz-import.yml` | 291 | 5 | Row-by-row upserts took 47-60 minutes. Four of five runs hit the 60 minute timeout. |
| `api-lint-test.yml` | 255 | 73 | Two jobs per run. Superseded pushes were not cancelled. |
| `web-ci.yml` | 200 | 48 | About 300 s per run. Superseded pushes were not cancelled. |
| `platform-maintenance.yml` | 107 | 17 | A daily `route` job plus a `skip` job, only to decide to do nothing. The 6-day cycle re-ran the OpenPLZ import about five times a month. |
| `keep-alive.yml` | 98 | 98 | One billed minute per ping. GitHub cron is best-effort, so Render was not kept warm. |
| `discovery-ingest-ci.yml` | 9 | 9 | Fine. |
| `discovery-drain.yml` | 0 | 0 | The crawler. Its schedule was off. |

GitHub bills per job and rounds up to a whole minute, so short jobs cost much more than their work.

## Measured in November (history)

`scripts/gha_minutes.py --since 2026-11-01` reads each run's timing through `gh` (read-only) and sums the billable minutes
per workflow. On 2026-11-13 GitHub's run timing reported zero billable minutes for every run checked, including successful
runs with a 786 s wall-clock time. No billed per-workflow figure could be taken from that endpoint. Under D17 no figure is
needed for this repository.

Completed runs from 2026-11-01 to 2026-11-13, counted from `gh run list`. The retired extract workflow (14 runs) is omitted:

| Workflow | Runs | Pull request runs | Cancelled | Skipped | Failed |
| --- | --- | --- | --- | --- | --- |
| `api-lint-test.yml` (API Lint & Test) | 110 | 97 | 0 | 0 | 8 |
| `discovery-ingest-ci.yml` | 75 | 60 | 0 | 0 | 3 |
| `web-ci.yml` | 60 | 51 | 0 | 0 | 4 |
| `discovery-render.yml` | 17 | 0 | 1 | 0 | 1 |
| `discovery-llm.yml` | 16 | 0 | 0 | 7 | 0 |
| `discovery-drain.yml` | 14 | 0 | 0 | 0 | 0 |
| `discovery-screenshot.yml` | 14 | 0 | 0 | 0 | 0 |
| `discovery-embed.yml` | 4 | 0 | 0 | 4 | 0 |
| `discovery-translate.yml` | 2 | 0 | 0 | 2 | 0 |

No pull request run was cancelled in this window. That does not show the cancellation is broken: the window may have had no
overlapping pushes. The concurrency block in `api-lint-test.yml` and `web-ci.yml` is unchanged.

## Minutes are not a budget

Under D17 the standard runners of this repository are not metered, so this page sets no minute cap and no per-drain minute share.
The stage workflows do not read the ledger's `actions_minutes` before they run (chapter 16), so no run skips for minutes.
The browser workflows skip under 30 browser seconds left. The neuron and character floors of the other stages are unchanged.

Each drain reports `ceil(elapsed / 60) + 1` minutes when it ends. Local runs report nothing and cost nothing.

## Workflow inventory

| Workflow | Trigger |
| --- | --- |
| `api-lint-test.yml`, `web-ci.yml`, `discovery-ingest-ci.yml` | `pull_request` and `push` to `main`, path filtered. A new push cancels the superseded PR run. |
| `platform-maintenance.yml` | Cron `0 2 28 * *` (monthly) and `workflow_dispatch` with `job` = `all`, `openplz` or `discovery`. The OpenPLZ job times out after 30 minutes; the import is incremental. |
| `discovery-daily.yml` | Two UTC slots, 03:17 and 15:17, when `PIPELINE_ORCHESTRATOR` is `enabled`, and `workflow_dispatch`. Shares the concurrency group `discovery-pipeline`. |
| `discovery-drain.yml` | Daily 02:00 UTC when `DISCOVERY_DRAIN_SCHEDULE` is `enabled`, and `workflow_dispatch`. Shares the concurrency group `discovery-pipeline`. |
| `discovery-render.yml` | Daily 03:00 UTC when `DISCOVERY_RENDER_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself under 30 browser seconds. Shares the concurrency group `discovery-pipeline`. |
| `discovery-llm.yml` | Daily 04:30 UTC when `DISCOVERY_LLM_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself under 300 neurons. Shares the concurrency group `discovery-pipeline`. |
| `discovery-screenshot.yml` | Daily 05:00 UTC when `DISCOVERY_SCREENSHOT_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself under 30 browser seconds. Shares the concurrency group `discovery-pipeline`. |
| `discovery-embed.yml` | 06:10 and 18:10 UTC when `DISCOVERY_EMBED_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself under 100 neurons, and when no embedding task is ready. Shares the concurrency group `discovery-pipeline`. |
| `discovery-translate.yml` | 17:10 UTC when `DISCOVERY_TRANSLATE_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself when the engine's own budget is short (`llm`: no more than 100 neurons above the `QUERY_EMBED_RESERVE` floor; `azure-translator`, the default: fewer characters than `AZURE_TRANSLATOR_MIN_REMAINING_CHARS` left this month), and when no translation task is ready. The snapshot job in the same file runs only when `SNAPSHOT_TRANSLATE_SCHEDULE` is `enabled`. Shares the concurrency group `discovery-pipeline`. |
| `discovery-storage-probe.yml`, `discovery-browser-probe.yml`, `discovery-fim-probe.yml`, `discovery-fixture-capture.yml` | `workflow_dispatch` only. Each is short and budget-neutral. |

`keep-alive.yml` and `openplz-import.yml` no longer exist. Schedules fire only from the default branch, so the release to
`main` is what turns them on.

## Embedding drain cadence (search-first, chapter 6)

`discovery-embed.yml` runs **twice a day** (06:10 and 18:10 UTC), not every six hours. The cost that decided it was the idle
run: even with an empty queue, a run pays for checkout, `pip install`, the ledger check, the Render wake-up
(`wait_for_api`, up to a minute on a cold start) and the queue precheck. Under D17 those minutes do not bill against a
limit, so the cadence is now set by the queue and the neuron budget.

| Run | Estimate (not yet measured) | Ledger minutes (`ceil(elapsed / 60) + 1`) |
| --- | --- | --- |
| Idle (the queue precheck skips the drain) | 1.5 to 2 minutes | 3 |
| Working, 3,000 neurons (about 2,700 texts of 1,500 characters, 54 batches of 50) | 5 to 8 minutes: about 1 s to embed a batch of 50 and a few seconds to post 50 vectors of 1024 numbers, plus the same setup | 7 to 10 |

A working run per day finishes about 2,700 texts, so the German backfill of about 4,700 candidates takes two days and the
six translated locales follow as translation lands. The neuron ledger, 9,500 a day shared with `llm_extract` and later
translation, is the real limit. To backfill faster, dispatch the workflow by hand or run `embed drain` on a laptop. It
costs no Actions minutes and shares the same ledger.

## Translation drain cadence (search-first, chapter 15)

`discovery-translate.yml` runs **once a day at 17:10 UTC**: after the 06:10 embed drain, an hour before the 18:10 one that
embeds the fresh translations (the group `discovery-pipeline` queues the embed run behind a translate run that is
still going, it does not cancel it). A run is bounded by `time_budget_seconds` 600 and `neuron_budget` 2,500.

The default engine, `azure-translator`, spends **characters**, not neurons: `neuron_budget` and the `QUERY_EMBED_RESERVE`
floor do not apply to it, and the monthly character ledger bounds it (see [translation-engines.md](translation-engines.md)).
The minutes below are estimates for `llm` runs. No `azure-translator` run has been measured yet.

| Run | Estimate (not yet measured) | Ledger minutes (`ceil(elapsed / 60) + 1`) |
| --- | --- | --- |
| Idle (the queue precheck skips the drain) | 1.5 to 2 minutes | 3 |
| Working, up to the 600 s budget | about 12 minutes: setup, then batches of 10 tasks, one Workers AI call per locale (about 5 to 8 s with the 1 s pacing) and one `complete` per locale, about 170 cards in six locales or 200 and more in fewer | 13 to 14 |

The neuron budget is what the chapter 13 probe decides: about 10 to 13 neurons per card and locale (the probe's own
prompts hold five cards; a batch of 10 tasks over six locales holds fewer cards per prompt, so the glossary overhead
repeats and the cost per card is a little higher), so a 2,500-neuron run translates about 200 cards and a six-locale
corpus of 4,713 cards (about 337,000 neurons) needs months at a free-tier pace. The first run is therefore
priority-limited by design: the queue is ordered highest confidence first, all locales of a candidate together, and
the operator narrows `TRANSLATION_TARGET_LOCALES` (decision D13) before enabling the schedule. The day's 9,500 neurons
are shared: `llm_extract` (up to 2,500), `embed drain` (up to 3,000), `translate drain` (up to 2,500) and the
**query-embedding floor** `QUERY_EMBED_RESERVE` (1,000), which the translate drain never takes the ledger below.

Minutes do not limit this schedule (D17). Neurons and characters do. Running `translate drain` on a laptop costs no
Actions minutes and shares the same ledger.

## Operator checklist

The steps below are the ones that still apply after the release. Schedules and flags are set only in
[pipeline-activation.md](pipeline-activation.md), in its order.

### O1 Account billing

This repository's minutes are not metered (D17). Remote checks still need the account to start Actions jobs. The run
ledger records billing-lock failures from 2026-11-15 to 2026-11-20. Before the release pull request, check **Settings,
Billing and licensing** for a failed payment or a spending limit, then confirm that a `workflow_dispatch` run starts.

### O2 External pinger

Create a free UptimeRobot (5 minute interval) or cron-job.org monitor on `https://redtape-api.onrender.com/health`. This replaces the removed keep-alive workflow. Details: [deployment-checklist.md](deployment-checklist.md).

### O3 Schedule and flag variables

Do not set schedule or flag variables from this page. The order is in [pipeline-activation.md](pipeline-activation.md).
Under **Settings, Secrets and variables, Actions, Variables**, `DISCOVERY_DRAIN_BUDGET_SECONDS` sets the scheduled drain's
wall-clock budget in seconds. When it is unset, the drain uses 900.

### O4 First live verification

Do this once, after the release reaches `main`.

1. Push two commits in quick succession to a PR. Confirm that the first CI run is `cancelled`.
2. Run `gh workflow run platform-maintenance.yml -f job=discovery`. Confirm that only the discovery job runs and that the Render health wait works.
3. Run `gh workflow run platform-maintenance.yml -f job=openplz` once. Record the duration. The target is under 15 minutes.
4. Run `gh workflow list`. Confirm that Keep Render API Awake and OpenPLZ Import are absent.

### O5 Retired monthly check

The monthly comparison of minutes is retired under D17. Nothing here needs a monthly figure from GitHub.

## Notes

- Free Supabase pauses a project after 7 idle days. A drain that runs at least weekly (scheduled or dispatched) reaches the database through the API and keeps it active.
- Free Render cold-starts after 15 idle minutes. The external pinger avoids most cold starts.
- The monthly platform-maintenance job runs on day 28 at 02:00 UTC.
