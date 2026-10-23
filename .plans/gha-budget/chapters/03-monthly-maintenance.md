---
name: "Chapter 3 — Monthly platform maintenance"
overview: "Replace the daily 6-day-cycle router with a monthly day-28 schedule that runs the OpenPLZ import and then the catalogue ingest, and delete the router."
todos:
  - id: workflow
    content: "Rewrite platform-maintenance.yml: monthly cron, job input, sequential jobs, no drain step"
    status: pending
  - id: router
    content: "Delete the router script and its test"
    status: pending
  - id: docs
    content: "Rewrite the workflow section of scheduled-jobs.md"
    status: pending
isProject: false
---

# Chapter 3 — Monthly platform maintenance

**Repo:** `redtape` (`.github/workflows`, `scripts`, `apps/api/tests`, `docs`) · **Branch:** `chore/gha-budget-monthly-maintenance` · **Status:** planned

**Depends on:** [2](02-retire-keep-alive-and-legacy-openplz.md) · **Decisions:** D2, D3, D4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `chore/gha-budget`

## Goal

The daily workflow spends two billed minutes (route plus skip) on four of six days to do nothing, and re-runs the 57 minute OpenPLZ import five times a month. The data changes rarely. Run once a month, late in the month.

## Design

Rewrite [platform-maintenance.yml](../../../.github/workflows/platform-maintenance.yml):

- `on.schedule`: `cron: "0 2 28 * *"` (day 28 exists in every month). `on.workflow_dispatch.inputs.job`: `type: choice`, `options: [all, openplz, discovery]`, `default: all`.
- Remove the `route` and `skip` jobs, the `MAINTENANCE_ANCHOR_DATE` env, and every `needs.route` reference.
- Job `openplz`: unchanged steps and env, `if: ${{ github.event_name == 'schedule' || inputs.job == 'all' || inputs.job == 'openplz' }}`, `timeout-minutes: 60` (lowered in chapter 5).
- Job `discovery`: `needs: openplz`, `if: ${{ !cancelled() && (github.event_name == 'schedule' || inputs.job == 'all' || inputs.job == 'discovery') }}` so a failed or skipped `openplz` never blocks it. Keep the job-level `concurrency: { group: discovery-drain, cancel-in-progress: false }`. Keep steps: checkout, Python, install, wait for Render API health, GovData fetch, PVOG run. **Delete the "Discovery worker drain" step** (D4). Set `timeout-minutes: 45`.
- Add `permissions: { contents: read }` at workflow level.

Delete `scripts/maintenance_job_router.py` and `apps/api/tests/test_maintenance_job_router.py`. If `scripts/` has no other file that needs the directory, leave the directory as is (other scripts exist).

Rewrite `docs/operations/scheduled-jobs.md`: the "Workflow" section (monthly cron, day 28, `job` input values), drop the `days % 6` table, update the secrets table headings (OpenPLZ job / Discovery job, no cycle-day labels), update "Manually triggering a run" (`gh workflow run platform-maintenance.yml -f job=openplz|discovery|all`), and say the worker drain is the job of `discovery-drain.yml`. Fix `docs/operations/discovery-online.md` and `docs/operations/discovery-online-production-setup.md` wherever they describe the 6-day cycle or the drain inside maintenance (`grep -rn "days % 6\|6-day\|six days\|sixth day\|maintenance_job_router" docs apps README.md`).

## Tests

No unit harness for the workflow. Gate: actionlint clean; the API section of `./ci.sh` green after deleting the router test (ruff, mypy `app scripts`, pytest with Postgres); `grep -rn "maintenance_job_router\|MAINTENANCE_ANCHOR_DATE\|needs.route"` finds nothing outside `.plans/`.

## Refactor gate

Audit the remaining `discovery` job for steps that only existed for the drain (env vars, health wait). The health wait stays (GovData and PVOG calls hit the API through ingest). Record the outcome.

## Commits

- `ci(maintenance): run platform maintenance monthly on day 28`
- `refactor(ci): remove the maintenance job router and its test`
- `docs(ops): describe monthly maintenance and the dedicated drain`
