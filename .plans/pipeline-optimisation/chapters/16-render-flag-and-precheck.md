---
name: "Chapter 16 — Render flag wiring and minute precheck removal"
overview: "Pass RENDER_FUSED_SCREENSHOT into the render job, default off, and remove the Actions-minutes check from the stage workflows, since minutes are not metered on the public repository."
id: C16
depends_on: []
touches:
  - .github/workflows/discovery-render.yml
  - .github/workflows/discovery-drain.yml
  - .github/workflows/discovery-screenshot.yml
  - .github/workflows/discovery-embed.yml
  - .github/workflows/discovery-translate.yml
  - .github/workflows/discovery-llm.yml
  - scripts/tests/
  - apps/discovery-ingest/tests/
execution: chapter-implementer
todos:
  - id: flag
    content: "Pass RENDER_FUSED_SCREENSHOT into the render job, default false"
    status: pending
  - id: precheck
    content: "Remove the actions_minutes check from the six stage workflows"
    status: pending
isProject: false
---

# Chapter 16 — Render flag wiring and minute precheck removal

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-render-flag` · **Status:** planned
**Depends on:** the loop branch at `997aeb87` (chapters 1 to 15 merged) · **Decisions:** D16, D17, D20

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

Two gaps block the activation walkthrough. Chapter 8's fused render flag is read by the config but no workflow passes it into the render job, so setting `RENDER_FUSED_SCREENSHOT` does nothing. And six stage workflows still refuse to run when the monthly Actions-minutes ledger is short, although minutes are not metered on this public repository (D17). Fix both, with no change to any cap, schedule or flag value.

## Design

- **Flag.** `discovery-render.yml` passes `RENDER_FUSED_SCREENSHOT: ${{ vars.RENDER_FUSED_SCREENSHOT || 'false' }}` into the render job. The default is off (D16). No repository variable is set by this chapter.
- **Precheck.** In each stage workflow, remove `--resource actions_minutes` and its `--require-remaining actions_minutes=N` from the `budget show` call. Keep every other resource and threshold: `browser_seconds`, `neurons`, `azure_translator_chars` and the translate engine check stay as they are. Where `actions_minutes` is the only resource (drain), remove the whole precheck step and every condition that reads its output.
- **Schedules and caps.** Do not touch any `schedule:` trigger, repository variable or budget cap.

## Files

**Edit**

- `.github/workflows/discovery-render.yml` (add the env line; remove the minutes resource)
- `.github/workflows/discovery-drain.yml` (remove the precheck step, which is minutes-only)
- `.github/workflows/discovery-screenshot.yml`, `discovery-embed.yml`, `discovery-translate.yml` (two calls), `discovery-llm.yml` (remove the minutes resource)
- Tests that pin the precheck text, under `scripts/tests/` and `apps/discovery-ingest/tests/`
- The docs that describe the precheck (`docs/operations/gha-budget.md`, `scheduled-jobs.md`): drop the minutes-gate sentence and keep the rest. The docs drift test (`scripts/tests/test_docs_drift.py`) must still pass.

## Red tests

| Test | Asserts |
| --- | --- |
| `the render job passes RENDER_FUSED_SCREENSHOT from its variable, defaulting to false` | Happy: the env line exists with the default. |
| `the render job never enables the fused path when the variable is unset` | Negative: the default value is `'false'`, so the config reads False. |
| `no stage workflow asks the budget for actions_minutes` | Negative grep over the six workflows: no `actions_minutes` in any `budget show` call. |
| `a stage still skips when its browser seconds are used up` | Happy: render and screenshot keep `browser_seconds=30` in their precheck. |
| `a stage still skips when its neuron budget is short` | Happy: embed and LLM keep `neurons=` in their precheck. |

## Green

1. Write the five tests, run them, and show they fail for the right reason.
2. Add the env line to the render workflow, then remove the minutes resource from each workflow, and the drain step.
3. Update the pinned tests and the two docs, then run the drift test.

## Refactor gate

Each workflow keeps one `budget show` call. If a precheck step is left with no resources, remove it rather than leave an empty call.

## Verification

```bash
python3 scripts/tests/test_docs_drift.py
cd apps/discovery-ingest && .venv/bin/python -m pytest -q tests/ -k "workflow or budget" && cd ../..
actionlint .github/workflows/discovery-*.yml        # docker image rhysd/actionlint:1.7.12, -no-color
VITEST_MAX_WORKERS=8 ./ci.sh all                    # Node 22 first on PATH
```

Live gate: none. No flag is turned on here.

## Commits

`test(ci): define the fused-flag env and the minutes-free precheck`, `ci: pass the fused render flag into the render job`, `ci: remove the actions minutes check from the stage workflows`, `docs(ops): drop the minutes gate from the scheduled-job docs`.

## Out of scope

Setting `RENDER_FUSED_SCREENSHOT` (chapter 8's canary gate does that), changing any cap, any schedule, the render failure investigation, and the stale extraction docs (a separate follow-up).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-render-flag
```

Integrate into the loop branch locally with `git merge --no-ff`, after the local gate passes.
