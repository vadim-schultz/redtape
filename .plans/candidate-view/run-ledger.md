# Run ledger

**Loop branch:** `feat/plans-candidate-view`  
**Release branch:** `main`  
**Release PR:** _(filled when opened)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file. The chief of staff records the screenshot live run here too.

| Chapter | Branch | PR | Local CI | Remote CI | Merged | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Capture requeue and machine route | `feat/candidate-view-capture-requeue` | [#263](https://github.com/vadim-schultz/redtape/pull/263) | pass (`./ci.sh` on scratch DB: api 1048, web 627, ingest 1156) | not run (Actions billing, D17) | yes, 704f25b | none |
| LR1. Screenshot collection ([02-live-runs.md](02-live-runs.md#lr1--screenshot-collection)) | n/a (live) | | | | | needs the API deployed (chapter 1); continuing with chapters that need no screenshots |
| 2. Completeness read model | `feat/candidate-view-completeness` | | | | | |
| 11. Manual curation tool | `feat/candidate-view-curation-tool` | | | | | |
| 3. Public candidate API | `feat/candidate-view-public-api` | | | | | |
| LR2. Showcase curation ([02-live-runs.md](02-live-runs.md#lr2--showcase-curation)) | docs PR `docs/candidate-view-showcase` | | | | | needs the API deployed (chapters 2, 3, 11) and LR1 |
| 4. Admin list contract | `feat/candidate-view-admin-list-contract` | | | | | |
| 5. Web candidate list | `feat/candidate-view-web-list` | | | | | |
| 6. Web candidate detail | `feat/candidate-view-web-detail` | | | | | |
| 7. Flow diagram | `feat/candidate-view-flow-diagram` | | | | | |
| 8. Admin documents table | `feat/candidate-view-admin-table` | | | | | |
| 9. Catalogue vs coverage | `feat/candidate-view-catalogue-coverage` | | | | | |
| 10. Docs and release | `docs/candidate-view-release` | | | | | |

## Live run records

**LR1, screenshots.** _(chief of staff fills: run IDs, screenshots before and after, pending and missing counts, browser seconds, bytes, one-image verdict, next date to repeat)_

**LR2, showcase candidates.** _(chief of staff fills: ranks and flags before and after, the chosen set with each candidate's role and `/candidates/<id>` path, codes and edge counts, the `curate` report line, the docs PR, capture result, one-image verdict, candidates still missing a screenshot)_

## Release checklist

- [ ] All chapter PRs are merged into the loop branch (verified with the host, not only the implementer's word).
- [ ] Each chapter reports a red, green, refactor outcome.
- [ ] Local gate green on the loop branch (`./ci.sh` on a scratch database if the local one is stale).
- [ ] Screenshot collection (LR1) and showcase curation (LR2) recorded above, or deferred with the blocker named.
- [ ] The showcase candidates are complete in the public list (five chips) and their paths are in the ledger for the smoke.
- [ ] Manual smoke (`docs/operations/candidate-view.md`, section Release smoke checks, written by chapter 10) performed by a human in light, dark and narrow layouts.
- [ ] Release PR opened from the loop branch to `main`; remote CI run if Actions minutes are back.
- [ ] Owner deploys API then web.

**Last orchestration:** 2026-10-30 — in progress; chapter 1 merged and verified, LR1 blocked on the owner's API deploy.
