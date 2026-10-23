# GitHub Actions budget and operator checklist

This repository runs on the GitHub Free plan: 2,000 Linux minutes a month, shared by every repository on the account. This page records where the minutes went, the target budget, and the steps that only the account owner can do. Workflow behaviour is in [scheduled-jobs.md](scheduled-jobs.md).

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

Assume about 960 minutes a month belong to this repository.

| Item | Min per month |
| --- | --- |
| CI (API, web, ingest) | ~330 |
| Platform maintenance (monthly OpenPLZ import and catalogue ingest) | ~65 |
| Keep-alive | 0 (external pinger) |
| Headroom | ~100 |
| **Crawl (`discovery-drain.yml`)** | **~465** |

The crawl figure is 15 minutes a day over 31 days. Days with an empty queue stop early on `queue_empty`. The cap is the repository variable `DISCOVERY_DRAIN_BUDGET_SECONDS`; see [Crawl budget](scheduled-jobs.md#crawl-budget).

## Workflow inventory

| Workflow | Trigger |
| --- | --- |
| `api-lint-test.yml`, `web-ci.yml`, `discovery-ingest-ci.yml` | `pull_request` and `push` to `main`, path filtered. A new push cancels the superseded PR run. |
| `platform-maintenance.yml` | Cron `0 2 28 * *` (monthly) and `workflow_dispatch` with `job` = `all`, `openplz` or `discovery`. The OpenPLZ job times out after 30 minutes; the import is incremental. |
| `discovery-drain.yml` | Daily 04:00 UTC when `DISCOVERY_DRAIN_SCHEDULE` is `enabled`, and `workflow_dispatch`. |

`keep-alive.yml` and `openplz-import.yml` no longer exist. Schedules fire only from the default branch, so the release to `main` is what saves minutes.

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
- `DISCOVERY_DRAIN_SCHEDULE`: leave unset until crawlers chapter 22 step S13. Setting it to `enabled` turns on the daily drain.

### O4 First live verification

Do this once, early in the month. It costs minutes.

1. Push two commits in quick succession to a PR. Confirm that the first CI run is `cancelled`.
2. Run `gh workflow run platform-maintenance.yml -f job=discovery`. Confirm that only the discovery job runs and that the Render health wait works.
3. Run `gh workflow run platform-maintenance.yml -f job=openplz` once. Record the duration. The target is under 15 minutes.
4. Run `gh workflow list`. Confirm that Keep Render API Awake and OpenPLZ Import are absent.

### O5 Monthly check

Compare the usage report with the targets: keep-alive 0, maintenance at most ~70, CI at most ~330, and the drain using the rest. Raise `DISCOVERY_DRAIN_BUDGET_SECONDS` when other repositories leave headroom.

## Notes

- Free Supabase pauses a project after 7 idle days. The daily drain reaches the database through the API and keeps it active.
- Free Render cold-starts after 15 idle minutes. The external pinger avoids most cold starts.
- `GITHUB_TOKEN` cannot read the remaining minutes. The heavy monthly job runs on day 28 to use leftover minutes; when the quota is gone it fails to start, which is harmless.
