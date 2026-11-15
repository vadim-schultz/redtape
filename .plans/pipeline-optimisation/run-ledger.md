# Run ledger

**Loop branch:** `feat/plans-pipeline-optimisation`
**Release branch:** `main`
**Release MR/PR:** _(filled when opened)_

**Gate change (from chapter 2):** GitHub Actions minutes are exhausted for November (1,981 of 2,000 used on 2026-11-13). Remote CI is not run, so the gate for each chapter is local `./ci.sh` only. Remote CI is recorded as "not run (Actions minutes exhausted)". A PR merges only if GitHub allows it without required checks; a refused merge is a blocker, not a bypass.

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1 CI minute diet | feat/pipeline-optimisation-ci-minute-diet | [#433](https://github.com/vadim-schultz/redtape/pull/433) | pass (`./ci.sh`, after excluding the retired-taxonomy repo scans in commit 23bbcef0) | pass (lint-and-test, lint-format-typecheck-build, change-set) | merged into loop branch (0ccc2ccb) | none. Open for operator: S1 usage report (`gha_minutes.py` reads zero from the run-timing endpoint); live gate after five PRs |
| 2 Observability and run hygiene | feat/pipeline-optimisation-observability | none (no PR; commits fast-forwarded into the loop branch by request) | pass for API (2159 passed, 29 skipped, earlier run) and discovery-ingest (2510 passed); web re-run clean: lint, format:check, typecheck, build pass; `npm test` 199 files, 1265 passed, 1 expected fail, exit 0 on three runs. One earlier run exited 1 with all tests passing, at load average 79, not reproduced. Focused API gate `REQUIRE_DB=1` against Postgres: 24 passed | not run (Actions minutes exhausted) | pushed to loop branch as f09d4fd9 (fast-forward, no merge commit) | none. Gate re-verified by chief of staff on 2026-11-15 after the chapter agent stopped before its return fields. Operator step: dispatch `discovery-screenshot.yml` once and record its run ID (needs Actions minutes; live gate, flag not involved) |
| 3 Neuron reconciliation spike | feat/pipeline-optimisation-neuron-spike | [#434](https://github.com/vadim-schultz/redtape/pull/434) | pass (`./ci.sh` exit 0: API 2159 passed, 29 skipped; web 1265 passed, 1 expected fail; ingest 2510 passed; scripts/tests 39 passed); `scripts/neuron_reconcile.py` ruff format and check pass | not run (Actions minutes exhausted); Cloudflare Workers Builds passed | merged into loop branch (861f6050, 2026-11-15 08:49Z) | none. Decision and figures below. Operator: `python3` on the python.org install fails Cloudflare's certificate check; the script ran with `/usr/bin/python3`. Fix the certificate store or accept `/usr/bin/python3` for this script. The script is 86 lines with its docstring (about 60 of code), slightly over the chapter's one-screen note |

## Chapter 3 decision (neuron reconciliation)

**Decision: build a rolling window** (a follow-up, not built here). Calibrating the estimate is not supported. Both the rolling reading and a fixed 12:00 UTC reset fit the evidence; a controlled check is still needed before chapter 12 relies on the window shape.

- **2026-11-11 refusal (11:20 UTC):** trailing 24 h in Cloudflare 11,315.18 (above 10,000), while the UTC day was 7,334.59 (below 9,500). The ledger read 7,302.57. A midnight reset is ruled out, because the day total is below 10,000. A fixed 12:00 UTC reset also fits, so the window edge is not yet separated from it.
- **2026-10-29 refusal (time not recorded):** trailing 24 h peaked at 12,702.0; the UTC day never exceeded 5,092.79. Consistent with a rolling window, not proof.
- **Calibration:** run-level settled totals match Cloudflare on 11-02, 11-03, 11-05 and 11-06 (within 0.1), but 11-04 differs by 103.52. Ledger error changes sign from day to day (10-28 −1,377.21; 10-29 +212.21; 10-30 −414.66; 11-11 −32.02), so no single calibration factor fits.
- **Unledgered spend (must close before any rolling budget is trusted):** `llm probe` (`apps/discovery-ingest/discovery_ingest/cli/llm/commands.py`, no guard; about 286 neurons on 10-28 while the ledger read 0), `embed probe` (about 9 neurons, 11-10), `translate probe --engine llm` (about 3,528 neurons across six locales on 11-10), the `discovery-llm-probe.yml` dispatch workflow (no runs recorded), and calls outside the CLI (about 411.5 unattributed on 10-30).
- **Translation refunds:** `translation/metered.py` refunds timeouts and 5xx failures even when Cloudflare billed them. A candidate for the 11-11 gap, not verified.
- **Not measured:** estimate-error counts per `llm_extract` task (the run reports do not carry them; the database was not read), and past-day ledger history (`budget show` returns the current period only).

**Follow-ups to schedule:** a controlled check that separates a rolling window from a 12:00 UTC reset; route the unledgered paths through the ledger; a history read for past-day ledger values. The chapter says a rolling-window decision moves to a follow-up chapter, and none exists in this suite yet.
