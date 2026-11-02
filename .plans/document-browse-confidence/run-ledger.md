# Run ledger

**Loop branch:** `feat/plans-document-browse-confidence`
**Release branch:** `main`
**Release MR/PR:** _(filled when opened)_

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| [06-menu-chrome](chapters/06-menu-chrome.md) | `feat/document-browse-confidence-menu-chrome` | [#314](https://github.com/vadim-schultz/redtape/pull/314) | pass (api pytest on fresh DB + web steps run by hand; shared dev DB schema stale) | pass | merged | none |
| [01-candidate-tag-scores](chapters/01-candidate-tag-scores.md) | `feat/document-browse-confidence-tag-scores` | [#315](https://github.com/vadim-schultz/redtape/pull/315) | pass (temp ci.sh copy against fresh DB; stock ci.sh blocked by stale dev DB) | pass | merged | none |
| [02-browse-contract](chapters/02-browse-contract.md) | `feat/document-browse-confidence-browse-contract` | [#316](https://github.com/vadim-schultz/redtape/pull/316) | pass (temp ci.sh copy, scratch DB) | pass | merged | none (deviation: grouped `best_scores` relation instead of correlated EXISTS, measured 25 s vs 0.3 s) |
| [03-documents-on-candidates](chapters/03-documents-on-candidates.md) | `feat/document-browse-confidence-documents-source` | [#317](https://github.com/vadim-schultz/redtape/pull/317) | pass (stock ./ci.sh) | pass | merged | none |
| [07-retire-candidates-list](chapters/07-retire-candidates-list.md) | `feat/document-browse-confidence-retire-candidates-list` | [#318](https://github.com/vadim-schultz/redtape/pull/318) | pass (temp ci.sh copy, scratch DBs) | pass | merged | none (kept CandidatesBanner, CandidateTagBadges, CompletenessChips: still used by item page) |
| [04-confidence-circle](chapters/04-confidence-circle.md) | `feat/document-browse-confidence-circle` | [#319](https://github.com/vadim-schultz/redtape/pull/319) | pass (temp ci.sh copy, scratch DBs) | pass | merged | none |
| [08-remove-seeded-documents](chapters/08-remove-seeded-documents.md) | `feat/document-browse-confidence-remove-seeded-documents` | [#321](https://github.com/vadim-schultz/redtape/pull/321) | pass (temp ci.sh copy, scratch DBs) | pass | merged | none (migration deletes 4 seeded docs by exact id; seed_taxonomy lost its `tags` arg) |
| [05-two-stage-chips](chapters/05-two-stage-chips.md) | `feat/document-browse-confidence-two-stage-chips` | [#320](https://github.com/vadim-schultz/redtape/pull/320) | pass (temp ci.sh copy, scratch DBs; last loop sync after ch8 covered by remote CI only) | pass (web checks; api jobs path-filtered) | merged | none (query key carries expanded situation codes; useDocumentFilters takes taxonomy) |
| [09-smell-sweep](chapters/09-smell-sweep.md) | `feat/document-browse-confidence-smell-sweep` | [#322](https://github.com/vadim-schultz/redtape/pull/322) | pass (stock ./ci.sh) | pass | merged | none |
| [10-docs-sync](chapters/10-docs-sync.md) | `feat/document-browse-confidence-docs-sync` | [#323](https://github.com/vadim-schultz/redtape/pull/323) | pass (stock ./ci.sh) | pass | merged | none |
| [11-live-validation](chapters/11-live-validation.md) | none (read-only) | — | — | — | not run | waits for release merge + deploy |
