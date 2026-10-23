# GitHub Actions budget — Run ledger

**Loop branch:** `chore/gha-budget`
**Release branch:** `main`
**Release PR:** _(filled when opened)_

Chapter PRs merge into the loop branch only. The chapter-implementer does not edit this file. **Remote CI is unavailable (shared Actions quota exhausted until about 2026-11-01); every gate is local.**

| chapter | branch | pr | local gate | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1 CI trim | `chore/gha-budget-ci-trim` | [#193](https://github.com/vadim-schultz/redtape/pull/193) | actionlint (docker) clean; no api/scripts changes | not available (billing) | yes, into `chore/gha-budget` 2026-10-23 | none |
| 2 Retire keep-alive and legacy OpenPLZ | `chore/gha-budget-retire-workflows` | [#194](https://github.com/vadim-schultz/redtape/pull/194) | actionlint (docker) clean; grep for dangling references empty; render.yaml parses | not available (billing) | yes, into `chore/gha-budget` 2026-10-23 | none |
| 3 Monthly maintenance | `chore/gha-budget-monthly-maintenance` | [#195](https://github.com/vadim-schultz/redtape/pull/195) | actionlint (docker) clean; ruff, mypy, `check_migrations.sh` and pytest (634 passed, `REQUIRE_DB=1`, fresh scratch database); grep for router references empty. Note: the local compose `redtape` database is stale (missing newer columns), so pytest ran on a scratch database | not available (billing) | yes, into `chore/gha-budget` 2026-10-23 | none |
| 4 Drain budget | `chore/gha-budget-drain-budget` | [#196](https://github.com/vadim-schultz/redtape/pull/196) | actionlint (docker) clean; workflow and docs only | not available (billing) | yes, into `chore/gha-budget` 2026-10-23 | none |
