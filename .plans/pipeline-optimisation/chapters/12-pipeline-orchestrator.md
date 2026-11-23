---
name: "Chapter 12 — Pipeline orchestrator and single workflow"
overview: "Run the stages in three phases from one daily job, with one deadline, one report and one budget call, and make every stage workflow dispatch-only."
todos:
  - id: plan
    content: "Compute the stage list from queue summaries and budgets"
    status: pending
  - id: run
    content: "Run the stages as subprocesses in three phases, forwarding signals"
    status: pending
  - id: workflow
    content: "Add one daily workflow and make the stage workflows dispatch-only"
    status: pending
isProject: false
---

# Chapter 12 — Pipeline orchestrator and single workflow

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-orchestrator` · **Status:** planned
**Depends on:** [1](01-ci-minute-diet.md), [2](02-observability-run-hygiene.md), [5](05-llm-readiness.md) (and 6, 7, 8 when they land) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3, item 3) · **Decisions:** D5, D16

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

Eight scheduled workflows each check out the repository, install the package and wait for the API, even when they then find no work. GitHub's cron also runs hours late, so the stages' ordering is a guess. Replace the schedules with one daily job that plans its stages from the queue summaries and budgets, runs them in three phases, and reports once.

## Design

- **Plan.** `discovery_ingest pipeline plan` calls the machine summaries (chapter 2) and the budget endpoint once. It emits the stages with ready work and their caps, and omits idle stages. Its output is JSON, so the workflow can log it.
- **Phases.** Phase 1 runs fetch and drain, the browser render (one process), embedding and the Azure card and page translation. Phase 2 runs `llm_extract` with concurrency, the screenshot sweeper and the Workers AI tail. Phase 3 runs a final pass of any stage with leftover ready work. Each phase starts only after the previous one ends.
- **Subprocesses.** Each stage is `python -m discovery_ingest <command>` run with its own flags. The orchestrator reads each stage's report from its output. Exit 1 only if a stage reports `succeeded=false`, and only after every stage has run.
- **Deadline.** The run has a fixed ceiling, `RUN_CEILING_SECONDS`, set below the job's `timeout-minutes`. No minute budget is computed, because Actions minutes are not metered on the public repository (D17). The orchestrator gives each stage the time left to that ceiling, capped at 20 minutes per stage. The YAML `timeout-minutes` stays as the backstop.
- **Signals.** SIGTERM and SIGINT are forwarded to the running stage and turned into a clean finish; the stage's run closes as failed (chapter 2).
- **Report.** One aggregated markdown summary to `GITHUB_STEP_SUMMARY` at the end. There is no minute report (D17).
- **Workflow.** `discovery-daily.yml` runs at one off-peak minute, with a second idempotent slot. Its concurrency group is `discovery-pipeline`. Every stage workflow loses its `schedule:` trigger and keeps `workflow_dispatch`. `discovery-extract.yml` is made dispatch-only here and deleted in chapter 15.
- **Flag.** The new workflow runs only when `PIPELINE_ORCHESTRATOR` is `enabled` (D16). The old schedules stay until the flag has run a full day.

## Files

**Create**

- `apps/discovery-ingest/discovery_ingest/cli/pipeline/__init__.py`, `commands.py` (`plan` and `run`)
- `apps/discovery-ingest/discovery_ingest/operations/pipeline.py` (the plan, the phases, the deadline)
- `.github/workflows/discovery-daily.yml`

**Edit**

- `apps/discovery-ingest/discovery_ingest/cli/main.py` (register the group)
- `.github/workflows/discovery-drain.yml`, `discovery-render.yml`, `discovery-extract.yml`, `discovery-llm.yml`, `discovery-screenshot.yml`, `discovery-embed.yml`, `discovery-translate.yml` (remove `schedule:`, keep `workflow_dispatch`)

**Do not edit**

- The individual drain implementations. The orchestrator calls them as they are.

## Red tests

| Test | Asserts |
| --- | --- |
| `plan omits a stage with no ready work` | Negative: an idle stage is not in the plan. |
| `plan includes a stage with ready work and its cap` | Happy. |
| `a failing stage does not stop the other stages` | Negative: the others still run, and the exit is 1 at the end. |
| `phase two starts only after phase one ends` | Happy: ordering with fake processes. |
| `the deadline gives each stage the time left, capped` | Happy and boundary, with a fake clock. |
| `SIGTERM closes the run as failed and exits` | Negative: the stage receives the signal and the run closes. |
| `the run summary is written once` | Happy: a single write to `GITHUB_STEP_SUMMARY`. |
| `the daily workflow does nothing when the flag is off` | Negative: the job condition is false. |

## Green

1. Write the plan tests against fake summaries, then the plan.
2. Write the phase and failure tests with fake processes, then the runner.
3. Write the deadline and signal tests, then add them.
4. Add the workflow. Keep every stage schedule in this merge (carried decision, run ledger of 2026-11-20). Chapter 15 removes them after the flag has run a full day.

## Refactor gate

The runner has one function per phase; the phases are data, not a chain of `if` statements. `cli/pipeline/commands.py` stays under about 100 lines.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest -q tests/ -k "pipeline" && cd ../..
actionlint .github/workflows/discovery-daily.yml .github/workflows/discovery-*.yml
./ci.sh
```

Live gate: enable `PIPELINE_ORCHESTRATOR` for one day with the stage schedules still on, and compare the day's stage reports. Remove the stage schedules only after a full day with no missed stage.

## Commits

`test(ingest): define the pipeline plan`, `feat(ingest): plan pipeline stages from queue summaries and budgets`, `test(ingest): define phased execution and failure isolation`, `feat(ingest): run pipeline stages in three phases`, `feat(ingest): add the daily pipeline workflow behind a flag`, `ci: make the stage workflows dispatch-only`.

## Out of scope

Retiring the stage workflows' files (chapter 15), changing any stage's own behaviour, and building a Worker-hosted runner (D8).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-orchestrator
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.

## Deviations

Recorded at implementation (chapter branch `feat/pipeline-optimisation-orchestrator`).

| # | Chapter says | Implemented | Reason |
| --- | --- | --- | --- |
| a | One fixed ceiling below the job's `timeout-minutes` (no value given) | `RUN_CEILING_SECONDS = 3300` (55 min); the job's `timeout-minutes: 60` | The ceiling must fire before the job timeout, with the margin for the grace periods |
| b | `plan` reads the summaries once; `run` is not specified | `run` re-reads the plan facts before each of the three phases | Phase two must see what phase one produced (render feeds extract and capture) |
| c | Remove the stage workflows' `schedule:` and add a `ci:` commit | No stage workflow is edited; no `ci:` commit | Carried decision (run ledger, 2026-11-20): keep every schedule until chapter 15 |
| d | The workflow runs only when `PIPELINE_ORCHESTRATOR` is `enabled` | Job-level `if: vars.PIPELINE_ORCHESTRATOR == 'enabled'`; manual dispatch is gated too | D16: off by default, for scheduled and manual runs alike |
| e | Single files `operations/pipeline.py` and `cli/pipeline/commands.py` | `operations/pipeline/` and `cli/pipeline/` are packages | The 100-line rule; the WIP draft already had the package |
| f | Read the flag and the summary path from the environment | Read through `IngestSettings` (`PIPELINE_ORCHESTRATOR`, `GITHUB_STEP_SUMMARY`) | `test_settings_layering` forbids `os.environ` outside config |
| g | Commit list of six | Seven commits: an extra `test(ingest): define the daily workflow gate` before the workflow commit | The workflow test is red before the workflow exists |
| h | Phase three: a final pass of any stage with leftover work | Phase three plans every stage from fresh facts; a stage that ran earlier may run again | Leftover work is the ready count after phase two |
| i | Exit 1 only if a stage reports `succeeded=false` | Exit 1 also when a stage prints no report or exits non-zero | A stage that prints nothing has not reported success |
| j | Tail locales are part of the plan | `tail_locales` is empty until chapter 7 names them, so `card_tail` is omitted as not configured | Chapter 7 has not landed |
| k | (not in chapter) | An unreachable API ends the run as failed, with one summary and no stage started | Data-design finding DD26: httpx errors escaped the run |
| l | (not in chapter) | A stage that ignores SIGTERM gets SIGKILL after `TERM_GRACE_SECONDS` (60 s) | Data-design finding: an unbounded wait held the run to the job timeout |
| m | Budget report called once | No Actions-minute report; one step summary only | D17: the repository is public, so there is no minute budget |
| n | (not in chapter) | The pinned CLI contract lists name the new group and commands: `GROUPS` gets `pipeline`, `COMMANDS` gets `pipeline plan` and `pipeline run` (count 30), and three golden help files are added for the new paths | The full ingest run failed three contract tests on the new group (coordinator-approved update, commit ec42d29e). Test names keep their older number words |
