# Run ledger

**Loop branch:** `feat/plans-web-gui-harmonization`  
**Release branch:** `main`  
**Release PR:** _(filled when the suite is complete)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file.

| Chapter | Branch | PR | Local CI | Remote CI | Merged | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Visual foundation | `feat/web-gui-harmonization-visual-foundation` | [#244](https://github.com/vadim-schultz/redtape/pull/244) | pass (`ci.sh` on fresh DB) | n/a (no Actions minutes) | merged 2026-10-29 | none |
| 2. DataTable kernel |  |  |  |  |  |  |
| 3. List contract |  |  |  |  |  |  |
| 4. Admin tables |  |  |  |  |  |  |
| 5. Coverage tables |  |  |  |  |  |  |
| 6. Table interactions |  |  |  |  |  |  |
| 7. Visual integration |  |  |  |  |  |  |
| 8. Release hardening |  |  |  |  |  |  |

## Release checklist

- [ ] All chapter PRs are merged into the loop branch.
- [ ] Each chapter reports a red → green → refactor outcome.
- [ ] Narrow and full local CI gates are green.
- [ ] Manual smoke checklist is complete in light/dark and narrow layouts.
- [ ] Existing visual-theme and menu-suite ownership links remain accurate.
- [ ] Release PR is opened from the loop branch to `main`.

