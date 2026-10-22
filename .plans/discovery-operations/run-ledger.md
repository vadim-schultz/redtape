# Discovery operations — Run ledger

**Loop branch:** `feat/discovery-operations`
**Release branch:** `main`

Update this ledger after every chapter implementation or documented operator verification. A chapter is not complete until its gate and refactor outcome are recorded.

| Chapter | Plan | Status | Verification | Refactor outcome | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | [Representative row end-to-end smoke](chapters/01-representative-row-smoke.md) | merged — blocked | PR [#177](https://github.com/vadim-schultz/redtape/pull/177) merged into `feat/discovery-operations`; local and remote checks green; fixture smoke is partial | no refactor needed — docs-only | Blocker: complete persisted T4/manual-emit smoke remains unverified because the fixture lacks `fim_id` and no authorized API/admin session was available |
| 2 | [Queue observability](chapters/02-queue-observability.md) | pending | — | — | |
| 3 | [Bounded repeatable worker drain](chapters/03-bounded-repeatable-drain.md) | pending | — | — | |
| 4 | [Discovery admin icon navigation](chapters/04-admin-icon-navigation.md) | pending | — | — | |
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
