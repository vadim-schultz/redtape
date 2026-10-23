---
name: "Chapter 4 — Drain budget"
overview: "Give the daily discovery drain a budget controlled by a repository variable, cache its pip install, and shorten its timeout, so the crawler gets a known share of the monthly minutes."
todos:
  - id: budget
    content: "Time budget from inputs, then DISCOVERY_DRAIN_BUDGET_SECONDS, then 900"
    status: pending
  - id: cache
    content: "cache: pip on setup-python, timeout-minutes 45"
    status: pending
  - id: docs
    content: "Document the budget table in scheduled-jobs.md"
    status: pending
isProject: false
---

# Chapter 4 — Drain budget

**Repo:** `redtape` (`.github/workflows`, `docs`) · **Branch:** `chore/gha-budget-drain-budget` · **Status:** planned

**Depends on:** [3](03-monthly-maintenance.md) · **Decisions:** D7, D8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `chore/gha-budget`

## Goal

[discovery-drain.yml](../../../.github/workflows/discovery-drain.yml) is the crawler. Its default budget is 1,500 s with a 90 minute timeout, which at one run a day would take about 750 min/month if the queue never empties; this repository's share is far smaller. Make the budget a repository variable with a conservative default so the owner can raise it without a code change.

## Design

- Env: `TIME_BUDGET_SECONDS: ${{ inputs.time_budget_seconds || vars.DISCOVERY_DRAIN_BUDGET_SECONDS || '900' }}`.
- The `workflow_dispatch` input `time_budget_seconds`: set `default: ""` and change its description to "Wall-clock budget in seconds (empty uses DISCOVERY_DRAIN_BUDGET_SECONDS, else 900)". An input default would otherwise always win over the variable.
- `setup-python`: add `cache: pip` and `cache-dependency-path: apps/discovery-ingest/pyproject.toml` (the pattern already used in `discovery-ingest-ci.yml`; no new action).
- `timeout-minutes: 90` → `45`.
- Keep: the daily `0 4 * * *` cron, the `DISCOVERY_DRAIN_SCHEDULE == 'enabled'` gate, the concurrency group, the report step, and the final success check.
- Docs: in `docs/operations/scheduled-jobs.md` add a "Crawl budget" section with the target table from [../00-architecture.md](../00-architecture.md) (about 465 crawl minutes a month at 15 minutes a day, idle days stop on `queue_empty`) and the two repository variables (`DISCOVERY_DRAIN_BUDGET_SECONDS`, `DISCOVERY_DRAIN_SCHEDULE`).

## Tests

No unit harness. Gate: actionlint clean. Read the final expression once more: an empty dispatch input must fall through to the variable and then to `'900'`. If the worker CLI rejects an empty `--time-budget-seconds`, that cannot occur here because the expression never yields an empty string.

## Refactor gate

Audit that the four env defaults (`MAX_TASKS`, `MAX_BATCHES`, `TIME_BUDGET_SECONDS`, `TASK_KINDS`) follow one pattern. Record the outcome.

## Commits

- `ci(discovery): budget the daily drain from a repository variable`
- `docs(ops): document the crawl budget and its variables`
