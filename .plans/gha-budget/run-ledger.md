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
| 5 OpenPLZ import speed-up | `chore/gha-budget-openplz-speedup` | [#197](https://github.com/vadim-schultz/redtape/pull/197) | actionlint clean; API ruff, mypy, pytest 647 passed on a scratch database (`REQUIRE_DB=1`); red tests first (6 failed for the right reason). Second import over identical input: SELECT 18 to 3, UPDATE 14 to 0. Independently re-run by the orchestrator: 25 OpenPLZ tests passed. Decision D11 recorded (`last_updated` is not an import-recency signal). Live timing deferred to operator step O4 | not available (billing) | yes, into `chore/gha-budget` 2026-10-23 | none |
| 6 Docs and operator steps | `chore/gha-budget-operator-steps` | [#198](https://github.com/vadim-schultz/redtape/pull/198) | actionlint (docker) clean; relative links in the new docs resolve; docs only | not available (billing) | yes, into `chore/gha-budget` 2026-10-23 | none |
