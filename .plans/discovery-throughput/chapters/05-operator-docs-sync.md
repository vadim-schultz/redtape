---
name: "Chapter 5 — Operator docs sync"
overview: "Bring every operator-facing doc in line with chapters 1-4's shipped shape before chapter 6 activates schedules from them."
todos:
  - id: scheduled-jobs
    content: "Rewrite scheduled-jobs.md's schedule and budget tables for the 5-workflow shape"
    status: pending
  - id: checklist
    content: "Add deployment-checklist.md lines for the two new schedule variables"
    status: pending
  - id: history
    content: "Append dated notes to gha-budget.md and gha-budget/00-architecture.md rather than rewriting history"
    status: pending
  - id: cross-ref
    content: "Note discovery-operations D7 as superseded by this suite's D5"
    status: pending
  - id: online-docs
    content: "Update discovery-online.md's LLM kind section"
    status: pending
isProject: false
---

# Chapter 5 — Operator docs sync

**Repo:** `redtape` (`docs`, `.plans`) · **Branch:** `feat/discovery-throughput-operator-docs-sync` · **Status:** planned

**Depends on:** [1](01-budget-reallocation.md), [2](02-same-day-pipeline-scheduling.md), [3](03-optional-situation-codes.md), [4](04-completeness-priority-claim.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-throughput`

## Goal

Make every existing operator-facing doc describe the shipped shape of chapters 1–4 accurately, so chapter 6's activation checklist isn't working from stale numbers or stale cron times.

## Design (docs only, no app code)

- `docs/operations/scheduled-jobs.md`: rewrite the worker-drains/budget-ledger table (five rows now, new times/kinds/timeouts per chapter 2's table), the "drain inputs" paragraph, the "Actions minutes" paragraph (2,000 shared-pool assumption / 1,000 repo share / 1,000 CI reserve / 1,000 drains), and the repository-variables table (add `DISCOVERY_EXTRACT_SCHEDULE`, `DISCOVERY_SCREENSHOT_SCHEDULE`; note that `DISCOVERY_RENDER_SCHEDULE`'s section now also controls whether `LLM_ENQUEUE` fires).
- `docs/operations/deployment-checklist.md`: confirm chapter 1's budget-number edits are present, and add checklist lines for `DISCOVERY_EXTRACT_SCHEDULE` / `DISCOVERY_SCREENSHOT_SCHEDULE` alongside the existing three schedule variables.
- `docs/operations/gha-budget.md` and [`gha-budget/00-architecture.md`](../../gha-budget/00-architecture.md): add one dated note each ("2026-11, revised again: this repository's share raised to 2,000/1,000/1,000, superseding the 2026-10-26 figures") rather than rewriting the historical tables — those stay as a record of what was true then.
- [`discovery-operations/gaps-and-decisions.md`](../../discovery-operations/gaps-and-decisions.md): add a one-line "superseded by `discovery-throughput` D5 (ordering clause only)" note next to D7, so a future reader doesn't assume ordering is still plain FIFO.
- `docs/operations/discovery-online.md` (the "LLM kind" section): update the "queueing" paragraph to state that `discovery-render.yml` now sets `LLM_ENQUEUE: "true"` by default (chapter 2), so scheduled renders do queue `llm_extract` work, and that `situation_codes` is now optional in the extraction output (chapter 3), cross-referencing `schema.py`.

## Tests

None — pure prose. The check is a grep for stale cron strings that should no longer describe the current schedule:

```bash
grep -rn "0 4 \* \* \*\|0 5 \* \* \*\|0 6 \* \* \*" docs/operations/scheduled-jobs.md docs/operations/deployment-checklist.md docs/operations/discovery-online.md
```

Any hit outside a dated historical note is a doc this chapter missed.

## Verification

Manual proofreading diff against the actual shipped YAML/config from chapters 1–4; no CI gate exists for prose beyond the grep above.

## Refactor gate

N/A — docs only.

## Commits

- `docs(operations): sync scheduled-jobs, deployment-checklist and discovery-online with the throughput changes`

## Out of scope

Any further code change; writing a new doc-link-check tool if none exists (use manual review, same as `discovery-operations` chapter 5's docs sync did).
