---
name: "Chapter 1 — Budget reallocation"
overview: "Change the scheduled/CI Actions-minutes split from 1000 total (400 usable for drains) to 2000 total, split 1000/1000, in code defaults and documentation."
todos:
  - id: config
    content: "Raise budget_actions_minutes_monthly to 2000 and actions_ci_reserve_minutes to 1000 in config.py"
    status: pending
  - id: tests
    content: "Update the two pinned-value tests to the new numbers"
    status: pending
  - id: docs
    content: "Sync deployment-checklist.md's budget table and add the operator Render-dashboard step"
    status: pending
isProject: false
---

# Chapter 1 — Budget reallocation

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-throughput-budget-reallocation` · **Status:** planned

**Depends on:** none · **Decisions:** D1, D2, D3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-throughput`

## Goal

Change the scheduled/CI Actions-minutes split from 1,000 total (600 CI reserve, 400 usable for drains) to 2,000 total, split 1,000/1,000, per [D1/D2](../gaps-and-decisions.md). The usable drain cap is derived live as `BUDGET_ACTIONS_MINUTES_MONTHLY − ACTIONS_CI_RESERVE_MINUTES` (`apps/api/app/features/discovery/budget_resources.py:39-40`, `_actions_minutes_cap`), so changing these two settings is the entire functional change; no other code reads or enforces the split.

## Design

- `apps/api/app/config.py:75-80` — `budget_actions_minutes_monthly` default `1_000 → 2_000`; `actions_ci_reserve_minutes` default `600 → 1_000`; update both `description=` strings to state the new split and reference that this repository's account-wide share is assumed to have grown (cross-reference D1).
- `docs/operations/deployment-checklist.md:87-88` — update the default-value column and the "drains may use 400" note to "drains may use 1000".
- Add one new operator checklist line (same file, same pattern as existing manual steps) telling the operator to set `BUDGET_ACTIONS_MINUTES_MONTHLY=2000` and `ACTIONS_CI_RESERVE_MINUTES=1000` in the Render dashboard, cross-referencing D1's unverified account-pool assumption. This line is a prerequisite for chapter 6, not something this chapter can execute itself (no Render API access).
- `render.yaml:49-51` — no functional change; confirm the comment still correctly says these are optional/dashboard-set.

## Tests

Update the two existing pinned-value tests — do not add new ones; both already pin the exact numbers this chapter changes:

- `apps/api/tests/test_budget_caps_ratio.py::test_the_actions_minutes_budget_stays_a_repository_share_of_the_account_pool` — currently asserts `(settings.budget_actions_minutes_monthly, settings.actions_ci_reserve_minutes) == (1_000, 600)`; change to `(2_000, 1_000)` and update its docstring/comment reasoning to the new split.
- `apps/api/tests/test_discovery_budgets.py::test_actions_minutes_cap_is_the_monthly_cap_minus_the_ci_reserve` — currently asserts `default.cap == 400` using `_service(db_session, budget_actions_minutes_monthly=1000, actions_ci_reserve_minutes=600)` (or the bare default); update the expected cap to `1000` against the new defaults, keeping the existing `_service(...)` helper pattern.

Red: edit both assertions to the new target values first and confirm they fail against the unchanged config defaults. Green: the two-line config change in `config.py` makes both pass.

## Verification

```bash
cd apps/api && ./ci.sh
python -c "from app.config import Settings; s=Settings(_env_file=None); print(s.budget_actions_minutes_monthly, s.actions_ci_reserve_minutes)"
# expect: 2000 1000
```

No live gate for this chapter — it changes defaults and docs, not a running service. The Render dashboard change itself is chapter 6's prerequisite checklist item, not this chapter's commit.

## Refactor gate

Trivial (two `Field` defaults and two description strings); no extraction needed.

## Commits

- `fix(config): raise the scheduled-task Actions-minutes budget to 2000/1000/1000`
- `docs(operations): sync the budget split across the deployment checklist`

## Out of scope

The actual Render dashboard change (operator step, referenced in chapter 6's prerequisites); any workflow YAML change (chapter 2); verifying the account-wide pool really has 2,000 minutes of headroom (flagged as an open seam in `gaps-and-decisions.md`, not resolved here).
