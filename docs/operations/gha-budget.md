# GitHub Actions budget and operator checklist

This repository runs on the GitHub Free plan: 2,000 Linux minutes a month, shared by every repository on the account. **This repository is capped at 1,000 minutes a month**, and a CI reserve inside that cap is not for drains. This page records where the minutes went, the budget, and the steps that only the account owner can do. Workflow behaviour and the budget ledger are in [scheduled-jobs.md](scheduled-jobs.md).

## What happened in October

The account reached 2,000 minutes a week early. This repository used 960 of them; the other repositories used about 1,040. When the quota is gone, every job fails in about 3 seconds with a billing error.

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

## Target budget

The cap is **1,000 minutes a month** for this repository (revised 2026-10-26). The budget ledger in the API enforces the
split below, so a drain workflow skips itself when its share is gone. The first estimate for this page was lower and is superseded; the 960 minutes of October are history.

| Item | Min per month | Notes |
| --- | --- | --- |
| **Repository cap** | **1,000** | `BUDGET_ACTIONS_MINUTES_MONTHLY` |
| CI reserve | 600 | `ACTIONS_CI_RESERVE_MINUTES`: API, web and ingest CI, monthly platform maintenance and headroom. Drains do not spend it |
| **Drain allowance** | **400** | Cap minus reserve: `discovery-drain.yml` and `discovery-render.yml` together |

The trimming targets were about 330 minutes for CI and about 65 for platform maintenance in a normal month. The crawlers suite adds about 17 pull
requests at 5 to 10 billed minutes each (web CI runs only when `apps/web` changes), which is why the reserve is 600.

A fifteen-minute drain bills about 16 minutes. The render backlog is about 22 such runs (about 5.5 hours) for the 1,423
known pages, which would use most of the allowance. Run the backlog on a laptop (checklist S18) and keep
`DISCOVERY_RENDER_SCHEDULE` unset. A drain skips itself when fewer than 45 minutes (render: 30) are left in the ledger.
Each drain reports `ceil(elapsed / 60) + 1` minutes when it ends. Local runs report nothing and cost nothing.

> **2026-11, revised again:** this repository's share raised to 2,000/1,000/1,000, superseding the 2026-10-26 figures
> above (`BUDGET_ACTIONS_MINUTES_MONTHLY=2000`, `ACTIONS_CI_RESERVE_MINUTES=1000`, a 1,000-minute drain allowance
> across the five `discovery-*.yml` workflows). The table above stays as the record of what was true on 2026-10-26;
> see [`discovery-throughput/gaps-and-decisions.md`](../../.plans/discovery-throughput/gaps-and-decisions.md) D1/D2
> and [scheduled-jobs.md](scheduled-jobs.md) for the current numbers.

Compare the ledger with GitHub's usage report once a month (checklist S20): `python -m discovery_ingest budget show`
prints `actions_minutes`; GitHub shows the repository's real minutes. If CI alone approaches the reserve, lower the
drain allowance (raise `ACTIONS_CI_RESERVE_MINUTES`), not the other way round. Raise `DISCOVERY_DRAIN_BUDGET_SECONDS`
only when the usage report shows headroom.

## Workflow inventory

| Workflow | Trigger |
| --- | --- |
| `api-lint-test.yml`, `web-ci.yml`, `discovery-ingest-ci.yml` | `pull_request` and `push` to `main`, path filtered. A new push cancels the superseded PR run. |
| `platform-maintenance.yml` | Cron `0 2 28 * *` (monthly) and `workflow_dispatch` with `job` = `all`, `openplz` or `discovery`. The OpenPLZ job times out after 30 minutes; the import is incremental. |
| `discovery-drain.yml` | Daily 04:00 UTC when `DISCOVERY_DRAIN_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself under 45 ledger minutes. |
| `discovery-embed.yml` | 06:10 and 18:10 UTC when `DISCOVERY_EMBED_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself under 20 ledger minutes or 100 neurons, and when no embedding task is ready. Shares the concurrency group `discovery-pipeline`. |
| `discovery-translate.yml` | 17:10 UTC when `DISCOVERY_TRANSLATE_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself under 20 ledger minutes, when the engine's own budget is short (`llm`: no more than 100 neurons above the `QUERY_EMBED_RESERVE` floor; `azure-translator`, the default: fewer characters than `AZURE_TRANSLATOR_MIN_REMAINING_CHARS` left this month), and when no translation task is ready. The snapshot job in the same file runs only when `SNAPSHOT_TRANSLATE_SCHEDULE` is `enabled`. Shares the concurrency group `discovery-pipeline`. |
| `discovery-render.yml` | Daily 05:00 UTC when `DISCOVERY_RENDER_SCHEDULE` is `enabled`, and `workflow_dispatch`. Skips itself under 30 ledger minutes or 30 browser seconds. Shares the concurrency group `discovery-drain`. |
| `discovery-storage-probe.yml`, `discovery-browser-probe.yml`, `discovery-fim-probe.yml`, `discovery-fixture-capture.yml` | `workflow_dispatch` only. Each is short and budget-neutral. |

`keep-alive.yml` and `openplz-import.yml` no longer exist. Schedules fire only from the default branch, so the release to `main` is what saves minutes.

## Embedding drain cadence (search-first, chapter 6)

`discovery-embed.yml` runs **twice a day** (06:10 and 18:10 UTC), not every six hours. The cost that decides it is the
idle run, because the queue is empty most of the time once the backfill is done: an idle run still pays for checkout,
`pip install`, the ledger check, the Render wake-up (`wait_for_api`, up to a minute on a cold start) and the queue
precheck, and the job is billed in whole minutes.

| Run | Estimate (not yet measured) | Ledger minutes (`ceil(elapsed / 60) + 1`) |
| --- | --- | --- |
| Idle (the queue precheck skips the drain) | 1.5 to 2 minutes | 3 |
| Working, 3,000 neurons (about 2,700 texts of 1,500 characters, 54 batches of 50) | 5 to 8 minutes: about 1 s to embed a batch of 50 and a few seconds to post 50 vectors of 1024 numbers, plus the same setup | 7 to 10 |

At two runs a day an always-idle month is about 60 runs, so about 180 ledger minutes (about 120 billed minutes) of the
1,000-minute drain allowance; every six hours would double that. A working run per day finishes about 2,700 texts, so
the German backfill of about 4,700 candidates takes two days and the six translated locales follow as translation lands
(the neuron ledger, 9,500 a day shared with `llm_extract` and later translation, is the real limit, not minutes). To
backfill faster, dispatch the workflow by hand or run `embed drain` on a laptop (it costs no Actions minutes and shares
the same ledger). **The measured minutes per run are recorded by the operator after the first runs** (the `Report
Actions minutes` step writes them to the ledger; `python -m discovery_ingest budget show --resource actions_minutes`
shows the total). If the allowance is tight, drop the schedule to once a day.

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

A month of working runs is about 30 x 14 = 420 ledger minutes of the 1,000-minute drain allowance on top of the other
drains: if the allowance is tight, lower `time_budget_seconds`, dispatch by hand, or unset
`DISCOVERY_TRANSLATE_SCHEDULE`. Running `translate drain` on a laptop costs no Actions minutes and shares the same
ledger. **The measured minutes per run are recorded by the operator after the first runs** (the `Report Actions minutes`
step writes them to the ledger).

## Operator checklist

No remote CI was available while this work was built, so none of the changed workflows has run on GitHub yet. Do these steps after the quota resets (about 2026-11-01).

### O1 Billing

1. Open GitHub **Settings -> Billing and licensing -> Usage**.
2. Check the usage of the other repositories on the account. Apply the same trimming: cancel superseded runs, avoid frequent crons, avoid polling workflows.
3. Consider a spending limit above $0 as a safety valve.
4. After the reset, confirm that a job starts instead of failing in 3 seconds.

### O2 External pinger

Create a free UptimeRobot (5 minute interval) or cron-job.org monitor on `https://redtape-api.onrender.com/health`. This replaces the removed keep-alive workflow. Details: [deployment-checklist.md](deployment-checklist.md).

### O3 Repository variables

Set under **Settings -> Secrets and variables -> Actions -> Variables**:

- `DISCOVERY_DRAIN_BUDGET_SECONDS`: seconds per scheduled drain. When unset, the drain uses 900.
- `DISCOVERY_DRAIN_SCHEDULE`: leave unset until [crawlers-operator-checklist.md](crawlers-operator-checklist.md) step S13. Setting it to `enabled` turns on the daily drain.
- `DISCOVERY_RENDER_SCHEDULE`: leave unset until there is budget (S13); the render backlog is cheaper on a laptop.

### O4 First live verification

Do this once, early in the month. It costs minutes.

1. Push two commits in quick succession to a PR. Confirm that the first CI run is `cancelled`.
2. Run `gh workflow run platform-maintenance.yml -f job=discovery`. Confirm that only the discovery job runs and that the Render health wait works.
3. Run `gh workflow run platform-maintenance.yml -f job=openplz` once. Record the duration. The target is under 15 minutes.
4. Run `gh workflow list`. Confirm that Keep Render API Awake and OpenPLZ Import are absent.

### O5 Monthly check

Compare the usage report with the targets: keep-alive 0, maintenance at most ~70, CI inside the 600 minute reserve, and the drains inside 400. Also compare the ledger's `actions_minutes` with GitHub's figure for the repository (S20). Raise `DISCOVERY_DRAIN_BUDGET_SECONDS` when other repositories leave headroom.

## Notes

- Free Supabase pauses a project after 7 idle days. A drain that runs at least weekly (scheduled or dispatched) reaches the database through the API and keeps it active.
- Free Render cold-starts after 15 idle minutes. The external pinger avoids most cold starts.
- `GITHUB_TOKEN` cannot read the remaining minutes. The heavy monthly job runs on day 28 to use leftover minutes; when the quota is gone it fails to start, which is harmless.
