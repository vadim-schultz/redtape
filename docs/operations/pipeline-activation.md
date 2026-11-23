# Pipeline activation walkthrough

This page turns the suite's activation into numbered steps, with one go or no-go check per step. Run the steps in
order and record each check in the run ledger before the next step. Flags default to off in code. Set repository
variables with `gh variable set NAME --body VALUE`. The operator steps S0 to S7 are listed at the end.

## Before anything

**Go when all three hold, then record them in the ledger:**

1. The release pull request from `feat/plans-pipeline-optimisation` to `main` is merged: `gh pr view <number> --json state,mergedAt,baseRefName` reports `MERGED` and `main`.
2. Render has redeployed the API. Its start script runs the migrations on every start, so check the deploy log for the new start.
3. Production is at the new alembic head, `20261119_fetch_body_sha256`. Production runs `20261112_locale_machine_flag` today. Check with `alembic current` against the production database, as [discovery-online.md](discovery-online.md) describes.

**No-go:** any check fails. Stop here. No stage flag or schedule changes.

**Refresh ceiling (D19, D18).** Set `CATALOGUE_REFRESH_MAX_ROWS` to `50` only after the three checks are recorded. The
ceiling is 50 pages a week; a failed refresh counts as the latest fetch.

## Before enabling any stage

**Render and screenshot failures.** Both fail at the "Drain browser tasks" step. Run list at 2026-11-23 (UTC): render
failed on 11-18, 11-19, 11-21, 11-22 and 11-23, skipped on 11-20; screenshot failed on 11-18, 11-20, 11-21 and 11-22,
skipped on 11-19, and succeeded once, on 11-23 at 15:39.

**Go when the cause is recorded in the ledger and a render run and a screenshot run both finish their drain step.**
Check with `gh run list --workflow discovery-render.yml --limit 5` and the same for `discovery-screenshot.yml`.

**No-go:** the cause is unknown, or a render run fails. Do not turn on `RENDER_FUSED_SCREENSHOT` (step 5) until this
passes.

## Step 1: LLM extraction (S2, chapter 5)

**Go when all hold:** the verification query (D2) returns no `ext-5` rows after 2026-11-06 12:23. Part C of
`c8_queries_4.sql`, from the taxonomy remediation ledger, is the query. `DISCOVERY_LLM_MODEL` is set, and the
[step 0 checks](#before-anything) are recorded.

Then set the schedule and dispatch one or two backfill runs for the backlog of about 400 tasks:

```bash
gh variable set DISCOVERY_LLM_SCHEDULE --body enabled
gh workflow run discovery-llm.yml -f neuron_budget=4500 -f time_budget_seconds=1000
```

**No-go:** the query returns rows, or the model variable is unset. The scheduled run skips itself when the model is missing.

## Step 2: Embeddings (S3, search-first chapter 6)

**Go when three manual `discovery-embed.yml` runs have cleared the backlog** of 4,713 tasks. The embeddings summary
(`GET …/embeddings/summary`) reports `pending_ready` of 0. Then:

```bash
gh variable set DISCOVERY_EMBED_SCHEDULE --body enabled
```

**No-go:** `pending_ready` is above 0 after the third run. Run again by hand; do not set the schedule.

## Step 3: Card translation (S4 and S6, chapter 6)

**Go only when all four hold:**

1. Chapter 6 is merged (run ledger, 2026-11-15). Done.
2. The Azure F0 reset date is read from the Azure portal (S6). The 2026-11-13 anchor is the operator's count. The monthly rule that follows from it is inferred, not confirmed.
3. The pacing decision is recorded. The pace uses the window anchored at `AZURE_WINDOW_ANCHOR` (2026-11-13), but the ledger resets on the calendar month. From 1 to 12 December the pace overstates what is left. Either accept that and record it, or make the change in a follow-up chapter before enabling.
4. `TRANSLATION_TAIL_LOCALES` is empty, as D14 requires, unless a locale has passed its probe (chapter 7).

```bash
gh variable set DISCOVERY_TRANSLATE_SCHEDULE --body enabled
```

**No-go:** any of the four is open. Leave the schedule unset and run `translate drain` by hand where needed.

## Step 4: One pipeline job for a day (chapter 12, D16, D20)

**Go when steps 1 to 3 are recorded or deliberately skipped.** Turn on `PIPELINE_ORCHESTRATOR` with every stage schedule
still on. The pipeline job runs at 03:17 and 15:17 UTC, in the shared group `discovery-pipeline`:

```bash
gh variable set PIPELINE_ORCHESTRATOR --body enabled
```

**Go to step 5 when a full UTC day has two pipeline runs that finish and no stage is missed.** Compare the pipeline
summary with each stage's drain report; a stage is missed when it has ready work and no report of a run or a named stop.

**No-go:** a pipeline run exits 1, or a stage shows a missing report. Set the variable back to unset and fix the
cause. The stage schedules keep running either way.

## Step 5: Fused render and screenshot (chapter 8)

**Go when the canary is recorded.** Run the canary with the flag still off:

```bash
python -m discovery_ingest browser probe --canary 25 --url <stable page> ...
```

Pass one `--url` for each of the 25 stable pages. Record the hash identity, the block and link counts, and browser
seconds per page in the ledger. Chapter 8's live gate is not run as of 2026-11-23.

**Code gap before this step.** No workflow passes `RENDER_FUSED_SCREENSHOT` into its job, so the repository variable
alone does nothing. A one-line `env` addition to `discovery-render.yml` comes first, as a code change.

**No-go:** the canary is not recorded, or the DOM parity differs (the gaps-and-decisions seam for chapter 8).

## Step 6: Remove the stage schedules (D20, last)

**Go only when step 4 has passed a full day with the stage schedules on,** and the recorded checks for steps 1 to 5 are
in the ledger. D20 makes this the last activation step.

1. Delete the stage schedule variables:

   ```bash
   gh variable delete DISCOVERY_DRAIN_SCHEDULE
   gh variable delete DISCOVERY_RENDER_SCHEDULE
   gh variable delete DISCOVERY_LLM_SCHEDULE
   gh variable delete DISCOVERY_EMBED_SCHEDULE
   gh variable delete DISCOVERY_TRANSLATE_SCHEDULE
   gh variable delete DISCOVERY_SCREENSHOT_SCHEDULE
   ```

2. Remove the `schedule:` triggers in a separate reviewed code commit. Keep `workflow_dispatch`.
3. Decide `SNAPSHOT_TRANSLATE_SCHEDULE` on its own. It is not a stage schedule.

**No-go:** the pipeline job missed a stage on any day. Keep every schedule on.

## Decision check: the Browser Sessions client (chapter 10)

**Before any decision to build a sessions client,** read Cloudflare's billed seconds for one session and compare them
with the client's session lifetime. The 2026-11-23 re-measure gave 54.5 seconds of lifetime for 50 pages, against
18.7 pages per billed minute for the quick actions. The billed figure is not read yet. The run ledger records
"do not record a go yet".

**Go to a sessions client only when** the billed seconds match the lifetime and pages per billed minute are at least
twice the quick-action figure. **No-go** otherwise. The local Chromium fallback is a separate question.

## Operator steps (architecture S0 to S7)

| Step | Owner | Status at 2026-11-23 |
| --- | --- | --- |
| S0 Pause the snapshot job for the first scheduled run | Repository owner | Time-bound to 2026-11-13. The ledger does not record a pause |
| S1 Read Actions usage | Account owner | Closed by D17. Not a constraint |
| S2 LLM schedule (step 1) | Repository owner | Open |
| S3 Embedding schedule (step 2) | Repository owner | Open |
| S4 Translate schedule (step 3) | Repository owner | Open, after chapter 6 and S6 |
| S5 Cloudflare tokens | Account owner | Tokens exist (crawlers checklist S15 and S16) |
| S6 Azure reset date (step 3) | Repository owner, in the Azure portal | Anchor 2026-11-13 from the operator; portal not confirmed |
| S7 Activation variables (steps 5 and 6) | Repository owner | Open. Retired variables after the release PR merges |

The retired extract variables are deleted after the release PR merges; their workflow is gone.
