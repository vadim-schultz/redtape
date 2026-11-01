---
name: "Chapter 6 — Schedule activation"
overview: "Turn on all five discovery schedules via gh variable set, once budget, pipeline order, leniency and priority are all shipped and documented."
todos:
  - id: render-budget
    content: "Confirm the Render dashboard has the 2000/1000 budget override set before proceeding"
    status: pending
  - id: variables
    content: "gh variable set every DISCOVERY_*_SCHEDULE var to enabled and set DISCOVERY_LLM_MODEL"
    status: pending
  - id: ledger
    content: "Record the activation and first day's run IDs in run-ledger.md"
    status: pending
isProject: false
---

# Chapter 6 — Schedule activation

**Repo:** `redtape` (GitHub repository variables; no file changes expected) · **Branch:** `feat/discovery-throughput-schedule-activation` · **Status:** planned

**Depends on:** [5](05-operator-docs-sync.md) · **Decisions:** D1 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-throughput`

## Goal

With budget, pipeline order, leniency, and priority all shipped and documented, turn every discovery schedule on — "now that we have GHA budget again, activate all the workflows."

## Design

This chapter's implementation is operator commands, not a repository commit — consistent with the manual-step pattern used throughout `docs/operations/*-checklist.md` and the live-gate steps in `.plans/crawlers`.

**Prerequisite, checked first:** confirm in the Render dashboard that `BUDGET_ACTIONS_MINUTES_MONTHLY=2000` and `ACTIONS_CI_RESERVE_MINUTES=1000` are actually set (chapter 1 only changed the code default; production needs the explicit override per D3). If this cannot be confirmed — no Render dashboard access in this session — record it as a blocked precondition in `run-ledger.md` rather than proceeding. Turning on five schedules against an unconfirmed budget risks repeating the account-wide lockout `docs/operations/gha-budget.md` already recorded once (ties to D1).

Once confirmed:

```bash
gh variable set DISCOVERY_DRAIN_SCHEDULE --body enabled
gh variable set DISCOVERY_RENDER_SCHEDULE --body enabled
gh variable set DISCOVERY_EXTRACT_SCHEDULE --body enabled
gh variable set DISCOVERY_LLM_SCHEDULE --body enabled
gh variable set DISCOVERY_SCREENSHOT_SCHEDULE --body enabled
gh variable set DISCOVERY_LLM_MODEL --body "@cf/qwen/qwen3-30b-a3b-fp8"
gh variable list
```

## Tests

None — no application code in this chapter. The "test" is the live state check:

```bash
gh variable list   # every DISCOVERY_*_SCHEDULE var reads "enabled"; DISCOVERY_LLM_MODEL is non-empty
```

## Verification

Live gate:

```bash
gh run list --workflow=discovery-drain.yml --limit 3
gh run list --workflow=discovery-render.yml --limit 3
gh run list --workflow=discovery-extract.yml --limit 3
gh run list --workflow=discovery-llm.yml --limit 3
gh run list --workflow=discovery-screenshot.yml --limit 3
```

After one full day, confirm a page fetched that morning reached `capture_screenshot` the same day. Record run IDs and the first day's `actions_minutes` ledger delta in `run-ledger.md`.

## Refactor gate

N/A — no code.

## Commits

None expected (pure `gh` state change). If `run-ledger.md` needs a line recording the activation date, that is a documentation commit:

- `docs(operations): record discovery schedule activation`

## Out of scope

Any code or YAML change (all prior chapters); diagnosing a real account-wide budget lockout if D1's assumption turns out false — that becomes an incident, not a chapter task.
