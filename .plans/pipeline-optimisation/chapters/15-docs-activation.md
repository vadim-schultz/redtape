---
name: "Chapter 15 — Docs, drift fixes and staged activation"
overview: "Bring the operator docs in line with the shipped pipeline, fix the known drift, delete the retired extract workflow, and walk through the staged activation with a go or no-go check at each step."
todos:
  - id: drift
    content: "Fix the drift list in the operator docs"
    status: pending
  - id: retire
    content: "Delete discovery-extract.yml and the variables that no longer apply"
    status: pending
  - id: activation
    content: "Run the activation walkthrough: LLM, embed, translate, then the pipeline flag"
    status: pending
isProject: false
---

# Chapter 15 — Docs, drift fixes and staged activation

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-docs-activation` · **Status:** planned
**Depends on:** all earlier chapters · **Decisions:** D9, D16

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

The operator docs describe the pipeline as it ran in November, and several of them are wrong: the cron times, the thresholds, the Actions cap, the LLM prompt and the render-to-screenshot path. Fix them, retire what the pipeline no longer uses, and turn the activation into a sequence with a go or no-go check at each step.

## Design

- **Drift list.** Fix these, each with a grep that proves it is gone:
  - `docs/operations/gha-budget.md`: the old drain and render times (04:00, 05:00), the group name `discovery-drain`, the 45-minute skip threshold, and the 1,000-minute cap table. Also replace its claim that Actions minutes bind: the repository is public, so standard runners are unmetered (D17).
  - `docs/operations/crawlers-operator-checklist.md`: the 1,000 and 600 figures in the S13 and S20 steps.
  - `docs/operations/extraction-operator-checklist.md`: the LLM time (06:00 should be 04:30) and the `LLM_ENQUEUE` rollback wording, which is hard-coded in the render workflow.
  - `docs/operations/candidate-view.md`: "no default drain handles `capture_screenshot`", which `discovery-screenshot.yml` now does.
  - `docs/operations/translation-engines.md:72`: "the hourly quota does not bind", which Azure's per-minute limit contradicts (chapter 6).
  - `.plans/search-first/chapters/06-embedding-drain-worker.md`: the 6-hour cadence, which shipped as 12.
- **Retire.** Delete `.github/workflows/discovery-extract.yml` (its registry is empty, `EXTRACTORS = ()`). Delete the repository variables `DISCOVERY_EXTRACT_SCHEDULE` and `DISCOVERY_EXTRACT_BUDGET_SECONDS` after the deletion is merged, and the old `*_SCHEDULE` variables after the daily workflow has run for a full week.
- **Activation walkthrough.** Written as numbered steps in `docs/operations/pipeline-activation.md`, one section per step, each with a go or no-go check:
  1. Confirm the LLM verification query (D2) and set `DISCOVERY_LLM_SCHEDULE`.
  2. Set `DISCOVERY_EMBED_SCHEDULE`, after three manual embed runs have cleared the backlog.
  3. Set `DISCOVERY_TRANSLATE_SCHEDULE` only after chapter 6 has merged and the Azure reset date is recorded (S6).
  4. Turn on `PIPELINE_ORCHESTRATOR` for one day with the stage schedules still on; compare the reports.
  5. Remove the stage schedules after a full day with no missed stage.
  6. Set `RENDER_FUSED_SCREENSHOT` after the canary is recorded (chapter 8).
- **Operator table.** The S0 to S7 steps from the architecture are listed in the walkthrough with their owners.
- **Suite status.** Each chapter's row in `01-rollout.md` shows its status, and `.plans/README.md` shows the suite as shipped.

## Files

**Edit**

- `docs/operations/gha-budget.md`, `scheduled-jobs.md`, `crawlers-operator-checklist.md`, `extraction-operator-checklist.md`, `candidate-view.md`, `translation-engines.md`, `deployment-checklist.md`
- `.plans/search-first/chapters/06-embedding-drain-worker.md`
- `.plans/pipeline-optimisation/01-rollout.md` (the status column)
- `.plans/README.md` (the suite's status)

**Create**

- `docs/operations/pipeline-activation.md`

**Delete**

- `.github/workflows/discovery-extract.yml`

## Red tests

| Test | Asserts |
| --- | --- |
| `no operator doc names the old cron times for drain or render` | Negative grep: `04:00` or `05:00` for drain or render is absent. |
| `no operator doc names the 1,000 cap as the repository cap` | Negative grep, with the allowed historical references listed. |
| `docs/operations/pipeline-activation.md has one section per activation step` | Happy: the six steps are present in order. |
| `discovery-extract.yml is absent` | Happy: the file is gone. |
| `the docs link check passes for every file in the suite and the operator docs` | Happy: no broken relative link or anchor. |

## Green

1. Write the grep tests as a script under `scripts/tests/`, run them, and see them fail on the current docs.
2. Fix each drift item and rerun until the grep passes.
3. Delete the extract workflow and its test, if one exists.
4. Write the activation walkthrough, then check every step has a go or no-go.

## Refactor gate

The grep checks live in one table, not one script per doc. The activation walkthrough stays one page; if it grows past about 150 lines, split it by step.

## Verification

```bash
python3 scripts/tests/test_docs_drift.py
./ci.sh
```

Gate: the grep tests pass; a link and anchor check passes over `docs/operations/` and `.plans/pipeline-optimisation/`; the activation page has all six steps. Then the activation walkthrough is run by the operator, and each step's check is recorded in the run ledger.

## Commits

`test(docs): define the drift checks for the operator docs`, `docs(ops): fix the drift in the scheduled-job and budget docs`, `docs(ops): add the pipeline activation walkthrough`, `ci: delete the retired extract workflow`.

## Out of scope

Changing any code path, changing the budget caps, and turning a flag on in code (the operator does that step by step).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-docs-activation
```

Open the chapter PR into `feat/plans-pipeline-optimisation`, then the release PR to `main` once every chapter's row is merged.
