---
name: GitHub Actions budget — Architecture
overview: "Why the shared Free Actions quota ran out, where the minutes went, and the target workflow inventory that leaves the largest share to the crawler."
isProject: false
---

# GitHub Actions budget — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

## Problem

The repository is private, on the GitHub Free plan: 2,000 Linux minutes per month, **shared by every repository on the account**. In October the account reached 2,000 minutes with a week to go. This repository used 960 of them; the other repositories used roughly 1,040. Once the quota is gone every job fails in about 3 seconds ("recent account payments have failed or your spending limit needs to be increased"), which blocked crawlers chapter 6 (PR #190).

| Workflow | Min (October) | Runs | Cause |
| --- | --- | --- | --- |
| `openplz-import.yml` | 291 | 5 | Row-by-row upserts over the Supabase pooler take 47–60 minutes. Four of five runs hit the 60 minute timeout and were cancelled. |
| `api-lint-test.yml` | 255 | 73 | Two jobs (about 133 s and 31 s, each billed rounded up). Superseded pushes are not cancelled. |
| `web-ci.yml` | 200 | 48 | About 300 s per run. Superseded pushes are not cancelled. |
| `platform-maintenance.yml` | 107 | 17 | A daily `route` job plus a `skip` job on four of six days, only to decide to do nothing. The 6-day cycle also re-runs the 57 minute OpenPLZ import about five times a month. |
| `keep-alive.yml` | 98 | 98 | One billed minute per ping. GitHub cron is best-effort (pings arrive every ~3 hours), so Render is not kept warm. `/health` never touches the database. |
| `discovery-ingest-ci.yml` | 9 | 9 | Fine. |
| `discovery-drain.yml` | 0 | 0 | The crawler. Not on `main` in October, its schedule is off. |

Billing is per job, rounded up to a whole minute, so short jobs are expensive relative to their work and a daily job that does nothing still costs two minutes.

## Target

This repository's share is the account quota minus the other repositories (assume about 960 minutes). Steady state per month:

| Item | Min |
| --- | --- |
| CI (API, web, ingest) | ~330 |
| Platform maintenance (monthly OpenPLZ import + catalogue ingest) | ~65 |
| Keep-alive | 0 (external pinger) |
| Headroom | ~100 |
| **Crawl (`discovery-drain.yml`)** | **~465** (15 min/day cap; idle days stop early on `queue_empty`) |

The crawl cap is the repository variable `DISCOVERY_DRAIN_BUDGET_SECONDS`, so it can be raised when other repositories use less.

## Target workflow inventory

| Workflow | Trigger after this suite |
| --- | --- |
| `api-lint-test.yml`, `web-ci.yml`, `discovery-ingest-ci.yml` | `pull_request` and `push` to `main` (path filtered), superseded PR runs cancelled |
| `platform-maintenance.yml` | cron `0 2 28 * *` (monthly) and `workflow_dispatch` with `job` = `all` / `openplz` / `discovery` |
| `discovery-drain.yml` | daily 04:00 UTC behind `DISCOVERY_DRAIN_SCHEDULE`, budget from `DISCOVERY_DRAIN_BUDGET_SECONDS` (default 900 s), `workflow_dispatch` |
| `keep-alive.yml`, `openplz-import.yml` | removed |

Render stays awake through an external free pinger (UptimeRobot or cron-job.org) on `/health`; that is an operator step, not code. Free Supabase pauses after 7 idle days; the daily drain reaches the database through the API and keeps it active.

## Constraints

- Schedules only fire from the default branch, so the release to `main` is what actually saves minutes.
- `GITHUB_TOKEN` cannot read remaining minutes. "Run only if minutes are left" is approximated by scheduling heavy jobs on day 28; when the quota is gone the job fails to start, harmlessly.
- **No remote CI exists until the quota resets (about 2026-11-01).** All gates in this suite are local.
