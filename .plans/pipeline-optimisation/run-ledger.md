# Run ledger

**Loop branch:** `feat/plans-pipeline-optimisation`
**Release branch:** `main`
**Release MR/PR:** _(filled when opened)_

**Gate change (from chapter 2):** GitHub Actions minutes are exhausted for November (1,981 of 2,000 used on 2026-11-13). Remote CI is not run, so the gate for each chapter is local `./ci.sh` only. Remote CI is recorded as "not run (Actions minutes exhausted)". A PR merges only if GitHub allows it without required checks; a refused merge is a blocker, not a bypass.

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1 CI minute diet | feat/pipeline-optimisation-ci-minute-diet | [#433](https://github.com/vadim-schultz/redtape/pull/433) | pass (`./ci.sh`, after excluding the retired-taxonomy repo scans in commit 23bbcef0) | pass (lint-and-test, lint-format-typecheck-build, change-set) | merged into loop branch (0ccc2ccb) | none. Open for operator: S1 usage report (`gha_minutes.py` reads zero from the run-timing endpoint); live gate after five PRs |
| 2 Observability and run hygiene | feat/pipeline-optimisation-observability | none (no PR; commits fast-forwarded into the loop branch by request) | pass for API (2159 passed, 29 skipped) and discovery-ingest; web vitest 197 files and 1257 tests passed but exited 1 on 2 worker-start timeouts under machine load (load average about 72) | not run (Actions minutes exhausted) | pushed to loop branch as f09d4fd9 (fast-forward, no merge commit) | web gate not re-run clean; re-run `./ci.sh` on a less loaded machine. Chapter agent was stopped before it reported its final return fields. Operator step: dispatch `discovery-screenshot.yml` once after merge and record its run ID (needs Actions minutes). |
