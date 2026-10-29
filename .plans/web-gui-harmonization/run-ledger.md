# Run ledger

**Loop branch:** `feat/plans-web-gui-harmonization`  
**Release branch:** `main`  
**Release PR:** _(filled when the suite is complete)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file.

| Chapter | Branch | PR | Local CI | Remote CI | Merged | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Visual foundation | `feat/web-gui-harmonization-visual-foundation` | [#244](https://github.com/vadim-schultz/redtape/pull/244) | pass (`ci.sh` on fresh DB) | n/a (no Actions minutes) | merged 2026-10-29 | none |
| 2. DataTable kernel | `feat/web-gui-harmonization-data-table` | [#245](https://github.com/vadim-schultz/redtape/pull/245) | pass (`ci.sh` on fresh DB) | n/a (no Actions minutes) | merged 2026-10-29 | none |
| 3. List contract | `feat/web-gui-harmonization-list-contract` | [#246](https://github.com/vadim-schultz/redtape/pull/246) | pass (`ci.sh` on fresh DB; narrow pytest 62 passed) | n/a (no Actions minutes) | merged 2026-10-29 | none |
| 4. Admin tables | `feat/web-gui-harmonization-admin-tables` | [#247](https://github.com/vadim-schultz/redtape/pull/247) | pass (`ci.sh` on fresh DB; stock run also hit one docs test, fixed in-PR) | n/a (no Actions minutes) | merged 2026-10-29 | none |
| 5. Coverage tables | `feat/web-gui-harmonization-coverage` | [#248](https://github.com/vadim-schultz/redtape/pull/248) | pass (`ci.sh` on fresh DB) | n/a (no Actions minutes) | merged 2026-10-29 | none |
| 6. Table interactions | `feat/web-gui-harmonization-table-interactions` | [#249](https://github.com/vadim-schultz/redtape/pull/249) | pass (`ci.sh` on fresh DB; narrow pytest 148 passed) | n/a (no Actions minutes) | merged 2026-10-29 | none |
| 7. Visual integration | `feat/web-gui-harmonization-visual-integration` | [#250](https://github.com/vadim-schultz/redtape/pull/250) | pass (`ci.sh` on fresh DB; manual smoke NOT performed) | n/a (no Actions minutes) | merged 2026-10-29 | none |
| 8. Release hardening | `feat/web-gui-harmonization-release-hardening` | [#251](https://github.com/vadim-schultz/redtape/pull/251) | pass (`ci.sh` on fresh DB; manual smoke NOT performed) | n/a (no Actions minutes) | merged 2026-10-29 | none |

## Release checklist

- [x] All chapter PRs are merged into the loop branch (#244–#251, verified via `gh pr view`).
- [x] Each chapter reports a red → green → refactor outcome.
- [x] Narrow and full local CI gates are green (no remote CI: Actions minutes exhausted; full `ci.sh` re-run on loop branch `01913ba` against a scratch DB — the long-lived local `redtape` DB has a stale schema).
- [ ] Manual smoke checklist is complete in light/dark and narrow layouts. **Pending a human** — no browser was available to any agent; checklist is in `docs/operations/admin-tables.md`.
- [x] Existing visual-theme and menu-suite ownership links remain accurate (menu-suite chevron fix `ec4154f` already in history).
- [ ] Release PR is opened from the loop branch to `main`.

