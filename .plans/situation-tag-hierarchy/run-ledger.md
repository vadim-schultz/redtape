# Run ledger

**Loop branch:** `feat/plans-situation-tag-hierarchy`
**Release branch:** `main`
**Release MR/PR:** not yet opened

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1 — Confidence scoring engine, and persisting it onto published documents | `feat/situation-tag-hierarchy-confidence-scoring-engine` | — | — | — | no | none |
| 2 — Life situation groups | `feat/situation-tag-hierarchy-life-situation-groups` | — | — | — | no | none |
| 3 — PVOG leaf refinement and domain-hint recovery | `feat/situation-tag-hierarchy-pvog-leaf-refinement` | — | — | — | no | none |
| 4 — Group-first browsing and confidence-ranked display | `feat/situation-tag-hierarchy-group-first-ui` | — | — | — | no | depends on 1–3 merged |
| 5 — Live validation | — | — | — | — | no | depends on 4 merged and deployed |
