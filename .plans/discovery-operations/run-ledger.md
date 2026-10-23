# Discovery operations — Run ledger

**Loop branch:** `feat/discovery-operations`
**Release branch:** `main`

Update this ledger after every chapter implementation or documented operator verification. A chapter is not complete until its gate and refactor outcome are recorded.

| Chapter | Plan | Status | Verification | Refactor outcome | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | [Representative row end-to-end smoke](chapters/01-representative-row-smoke.md) | merged — accepted partial | PR [#177](https://github.com/vadim-schultz/redtape/pull/177) merged into `feat/discovery-operations`; local and remote checks green; fixture smoke is partial | no refactor needed — docs-only | Accepted by user 2026-10-23 as partial T0/T1/T2 smoke; complete persisted T4/manual-emit smoke remains unverified because the fixture lacks `fim_id` and no authorized API/admin session was available |
| 2 | [Queue observability](chapters/02-queue-observability.md) | merged | PR [#178](https://github.com/vadim-schultz/redtape/pull/178) merged into `feat/discovery-operations`; remote CI green; local `./ci.sh` ingest step failed on PyPI DNS (environmental), same ingest checks pass from `.venv` | audited; extracted QueueMetricsRepository, RunRepository, DiscoveryRunService | Adds `discovery_run` table and `stale_runs` |
| 3 | [Bounded repeatable worker drain](chapters/03-bounded-repeatable-drain.md) | merged | PR [#179](https://github.com/vadim-schultz/redtape/pull/179) merged into `feat/discovery-operations`; only Cloudflare check ran (no GitHub workflow covers `apps/discovery-ingest`); local `./ci.sh` ingest step failed on PyPI DNS, ingest ruff/mypy/pytest (51) pass from `.venv` | audited; extracted DrainPolicy, _Tally, _run_batch | Gaps: no separate red step per loop; manual multi-batch and interrupted-claim lease-reclaim check not performed; `remaining` unknown (no queue-summary route) |
| 4 | [Discovery admin icon navigation](chapters/04-admin-icon-navigation.md) | merged | PR [#180](https://github.com/vadim-schultz/redtape/pull/180) merged into `feat/discovery-operations`; remote CI green; web lint/format/typecheck/tests/build pass locally; `./ci.sh` ingest step failed on PyPI DNS (no ingest changes) | audited; config array owns route/icon/label, no extraction needed | Red test run before implementation |
| 5 | [T4 handoff and operations docs sync](chapters/05-t4-handoff-and-docs-sync.md) | pending | — | — | |

## Release checklist

- [ ] Chapter 1 smoke evidence records one row from source ingest to pending suggestion.
- [ ] Chapter 2 metrics and run lifecycle are observable through the agreed API/admin surfaces.
- [ ] Chapter 3 bounded drain makes repeatable progress and handles invalid bounds/no-progress safely.
- [ ] Chapter 4 icon controls preserve route, auth, locale, keyboard, and screen-reader behavior.
- [ ] Chapter 5 operations docs and links are synchronized.
- [ ] Relevant package checks and root `./ci.sh` are green where implementation chapters changed code.
- [ ] Crawler, screenshot/evidence, automatic emit, moderation, and promotion remain out of scope.
- [ ] Release PR from `feat/discovery-operations` to `main` is ready.
