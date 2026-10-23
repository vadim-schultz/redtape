---
name: "Chapter 6 — Docs and operator steps"
overview: "Finalise the budget documentation and write the operator checklist for the steps only the account owner can do, including the first live verification after the quota resets."
todos:
  - id: docs
    content: "Final pass on scheduled-jobs.md and the plans README"
    status: pending
  - id: operator
    content: "Write docs/operations/gha-budget.md with the operator checklist O1-O5"
    status: pending
isProject: false
---

# Chapter 6 — Docs and operator steps

**Repo:** `redtape` (`docs`, `.plans`) · **Branch:** `chore/gha-budget-operator-steps` · **Status:** planned

**Depends on:** [1](01-ci-trim.md), [4](04-drain-budget.md), [5](05-openplz-import-speedup.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `chore/gha-budget`

## Goal

Several steps cannot be done by code: the billing state, the external pinger, repository variables, and the first live runs of workflows that could not be run while the quota was exhausted. Write them down where the owner and the next chief-of-staff run will find them.

## Design

Create `docs/operations/gha-budget.md` (and link it from `docs/operations/scheduled-jobs.md` Related list) containing:

1. **Why and what changed:** the October table (from [../00-architecture.md](../00-architecture.md)), the target budget, the final workflow inventory.
2. **Operator checklist**, each step with its command or place:
   - **O1 Billing.** GitHub → Settings → Billing and licensing → Usage: the 2,000 Free minutes are shared by all repositories; check the other repositories' usage and apply the same trimming (cancel superseded runs, no frequent crons, no polling workflows). Consider a spending limit above $0 as a safety valve. After the reset (about 2026-11-01) confirm a job starts instead of failing in 3 s.
   - **O2 External pinger.** Free UptimeRobot (5 min) or cron-job.org monitor on `https://redtape-api.onrender.com/health`.
   - **O3 Repository variables.** `DISCOVERY_DRAIN_BUDGET_SECONDS` (default 900 when unset). Leave `DISCOVERY_DRAIN_SCHEDULE` unset until crawlers chapter 22 step S13.
   - **O4 First live verification** (costs minutes, do it once, early in the month): push two commits to a PR and confirm the first CI run is `cancelled`; `gh workflow run platform-maintenance.yml -f job=discovery` and confirm only that job runs and the Render health wait works; `gh workflow run platform-maintenance.yml -f job=openplz` once and record the duration (target under 15 minutes); `gh workflow list` shows no Keep Render API Awake or OpenPLZ Import.
   - **O5 Monthly check.** Compare the usage report with the targets: keep-alive 0, maintenance ≤ ~70, CI ≤ ~330, drain using the rest; raise `DISCOVERY_DRAIN_BUDGET_SECONDS` when headroom allows.
3. **Notes:** free Supabase pauses after 7 idle days and the daily drain (through the API) keeps it active; free Render cold-starts after 15 idle minutes.

Also update `.plans/README.md` status for this suite to "shipped" with a pointer to the operator doc, and `docs/planning/STATUS.md` only if it still claims a keep-alive cron.

## Tests

No unit harness. Gate: all relative links in the new doc resolve (`grep -o "](\([^)]*\))"` plus `test -e`), actionlint still clean on all workflows.

## Refactor gate

Audit that `scheduled-jobs.md` and `gha-budget.md` do not duplicate the budget table; keep it in one and link from the other.

## Commits

- `docs(ops): add the Actions budget and operator checklist`
- `docs(plans): mark the gha-budget suite shipped`
