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
