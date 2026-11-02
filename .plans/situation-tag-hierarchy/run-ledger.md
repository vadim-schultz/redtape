# Run ledger

**Loop branch:** `feat/plans-situation-tag-hierarchy`
**Release branch:** `main`
**Release MR/PR:** opening now — chapter 5 (live validation) is deferred: it requires hand-labelling production data and manually checking the deployed UI, which isn't code-chapter work. Per user decision (vadim.schultz, 2026-11-02), the release PR opens now rather than waiting on it; chapter 5's results will be recorded in `02-live-runs.md` and `gaps-and-decisions.md` P1 once the user runs it post-deploy.

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1 — Confidence scoring engine, and persisting it onto published documents | `feat/situation-tag-hierarchy-confidence-scoring-engine` | [#308](https://github.com/vadim-schultz/redtape/pull/308) | pass | pass | yes | none |
| 2 — Life situation groups | `feat/situation-tag-hierarchy-life-situation-groups` | [#309](https://github.com/vadim-schultz/redtape/pull/309) | pass | pass | yes | none |
| 3 — PVOG leaf refinement and domain-hint recovery | `feat/situation-tag-hierarchy-pvog-leaf-refinement` | [#310](https://github.com/vadim-schultz/redtape/pull/310) | pass | pass | yes | none |
| 4 — Group-first browsing and confidence-ranked display | `feat/situation-tag-hierarchy-group-first-ui` | [#311](https://github.com/vadim-schultz/redtape/pull/311) | pass | pass | yes | none |
| 5 — Live validation | — | — | — | — | no | depends on 4 merged and deployed |
