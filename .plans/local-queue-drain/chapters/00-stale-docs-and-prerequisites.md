# C0 — Stale docs and operator prerequisites

**Depends on:** none · **Batch:** 0 · **Branch:** `chore/local-queue-drain-stale-docs`

## Goal

Correct the operator docs and tests that still describe the Actions minute cap, and record the prerequisites that the local workers need from the operator. No behaviour changes.

## Preconditions

- Operator confirms D1 (hosted minutes are unmetered) and records it in the ledger.
- Operator creates a machine key for local workers (D15) and gives its name, not its value, to the plan.

## Scope

1. **Docs.** Rewrite the minute-cap passages in the files listed in the architecture, section 9. Replace them with the binding limits: Browser Run seconds, Workers AI neurons and Azure characters. Object storage is out of this plan (D13). Keep history sections, and mark them superseded.
2. **Workflow steps.** Remove the minute prechecks and the `budget report-minutes` step from the discovery workflows. Pipeline-optimisation chapter 16 covers part of this; take over what it left.
3. **Tests that assert doc or budget text.** `test_budget_caps_ratio.py` and `test_crawlers_docs.py` assert the old wording or share. Update them red-first: change the assertion, watch it fail for the old text, then update the doc.
4. **Enum and config.** Keep `actions_minutes` (O6). Add a docstring to `_actions_minutes_cap` saying the resource is obsolete.

## Red

Docs-only chapter. The red step is a grep and a test run:

- `grep -rIn -E "1,000 min|2,000 minutes|report-minutes|minute precheck" docs .github apps/api/tests` lists the files in the architecture, section 9. The command is the red signal.
- Update `test_budget_caps_ratio.py` to assert the new statement (no repository share of Actions minutes is enforced). Run it. It fails on the old code for the right reason: the assertion no longer matches the text.

## Green

- Rewrite the docs listed in scope. Remove the workflow steps. Update the tests to pass.
- Run the grep again. It must print no operator-facing hit. History under `.plans/` may keep its text, marked superseded.

## Refactor

- The discovery workflows repeat the same budget-check shell block. Extract it into one composite step if the step count drops by more than two. Otherwise leave it.
- Check the operator checklists for duplicated steps about the minute cap, and merge them.

## Verification

```bash
cd apps/api && ./ci.sh          # or the narrowest pytest command covering the changed tests
cd /mnt/projects/redtape-wt/local-queue-drain && ./ci.sh lint   # if the lint entry point exists
grep -rIn -E "1,000 min|2,000 minutes|report-minutes|minute precheck" docs .github apps/api/tests | grep -v ".plans/"
```

The last command must print nothing.

## Exit

- The stale-wording grep is clean outside `.plans/` history.
- The operator has the machine key name and the confirmation of D1 in the ledger.
