# Run ledger

**Loop branch:** `feat/plans-situation-tag-activation`
**Release branch:** `main`
**Release MR/PR:** _(filled when opened)_

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1 — Unify the consensus engine, then make it axis-aware | `feat/situation-tag-activation-axis-aware-consensus-thresholds` | https://github.com/vadim-schultz/redtape/pull/302 | pass | pass | yes (loop) | none |
| 2 — Tag confidence tier on the suggestion payload | `feat/situation-tag-activation-tag-confidence-tier` | https://github.com/vadim-schultz/redtape/pull/303 | pass | pass | yes (loop) | none |
| 3 — PVOG `personalMatters` as an independent situation signal | `feat/situation-tag-activation-pvog-situation-signal` | https://github.com/vadim-schultz/redtape/pull/304 | pass | pass | yes (loop) | none for merge — PVOG/LLM overlap count still unmeasured (needs production DB access), recorded as an open seam, not gating this chapter |
