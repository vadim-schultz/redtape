---
name: GitHub Actions budget — Gaps and decisions
overview: "Settled decisions and open seams for the Actions budget suite."
isProject: false
---

# GitHub Actions budget — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **Keep-alive leaves GitHub Actions.** GitHub cron cannot hold a 10 minute cadence and each ping bills a minute. An external free pinger on `/health` (operator step) replaces it. Deleted, not trimmed. |
| D2 | **Platform maintenance is monthly,** cron `0 2 28 * *`. The data (municipalities, catalogue) changes rarely; day 28 spends leftover minutes late in the month. No router, no skip job. |
| D3 | **The monthly job runs OpenPLZ first, then the catalogue ingest.** `discovery` needs `openplz` but runs even when it failed or was skipped (`!cancelled()`). |
| D4 | **The dedicated drain replaces the drain step in maintenance.** Maintenance keeps GovData fetch and PVOG run only, so the same drain is never paid for twice. |
| D5 | **The legacy `openplz-import.yml` is deleted.** It duplicates the maintenance `openplz` job; manual runs use `gh workflow run platform-maintenance.yml -f job=openplz`. |
| D6 | **CI changes are limited to concurrency and trigger cleanup.** Superseded PR runs are cancelled; pushes to `main` are not. The `migrations` job stays separate (commit e84cd70), `npm install` stays (documented `npm ci` flakiness). Dependency caching for `uv` was rejected: it saves seconds on jobs billed per whole minute and needs a new action. |
| D7 | **No new third-party actions and no new action majors.** Nothing can be run remotely before the quota resets, so every workflow edit must be conservative. |
| D8 | **The crawl budget is a repository variable** (`DISCOVERY_DRAIN_BUDGET_SECONDS`, fallback 900 s), never hard-coded. The dispatch input default is empty so the variable takes effect. |
| D9 | **OpenPLZ import is made incremental** (preload, write only changed rows) instead of moving it off GitHub. Decision on `last_updated` is taken in chapter 5 after auditing its readers. |
| D10 | **No remote CI in this suite.** Local gates only; implementers never dispatch workflows or wait on `gh pr checks`. |

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Billing-API guard ("run only if minutes remain") | Day-28 scheduling and a harmless failure when the quota is gone | A PAT with plan-read scope is acceptable |
| Running the crawler outside GitHub (laptop, Render cron) | Not planned | The crawl share stays too small |
| First live run of every changed workflow | Operator checklist O4 in chapter 6 | The quota resets (about 2026-11-01) |
