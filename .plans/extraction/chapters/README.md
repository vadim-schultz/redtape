# Extraction — chapters

One executable plan per chapter. Order, dependencies and gates: [../01-rollout.md](../01-rollout.md). Decisions: [../gaps-and-decisions.md](../gaps-and-decisions.md). Ledger: [../run-ledger.md](../run-ledger.md).

| # | File | Layer |
| --- | --- | --- |
| E1 | [01-staging-groundwork.md](01-staging-groundwork.md) | model + migration + API |
| E2 | [02-page-cleaner.md](02-page-cleaner.md) | worker |
| E3 | [03-extraction-schema-and-grounding.md](03-extraction-schema-and-grounding.md) | worker |
| E4 | [04-workers-ai-client-and-probe.md](04-workers-ai-client-and-probe.md) | worker + CI workflow |
| E5 | [05-eval-harness-and-model-choice.md](05-eval-harness-and-model-choice.md) | worker |
| E6 | [06-llm-extract-handler.md](06-llm-extract-handler.md) | worker |
| E7 | [07-wiring-and-workflow.md](07-wiring-and-workflow.md) | worker + CI workflow |
| E8 | [08-admin-display.md](08-admin-display.md) | API + frontend |
| E9 | [09-docs-and-operator-steps.md](09-docs-and-operator-steps.md) | docs + ops |
| E10 | [10-robots-rules-fix.md](10-robots-rules-fix.md) | worker (executes second) |
| E11 | [11-free-tier-caps-95.md](11-free-tier-caps-95.md) | config + workflow + docs (executes first) |
| E12 | [12-extraction-quality-tuning.md](12-extraction-quality-tuning.md) | worker (after E6) |
| E13 | [13-grounding-normalisation.md](13-grounding-normalisation.md) | worker (after E12) |
| E14 | [14-raise-the-input-cap.md](14-raise-the-input-cap.md) | worker + docs (after E13) |
| E15 | [15-quote-shape.md](15-quote-shape.md) | worker (after E14) |
| E16 | [16-documents-not-data-fields.md](16-documents-not-data-fields.md) | worker (after E7) |
| E17 | [17-price-rows-for-candidate-models.md](17-price-rows-for-candidate-models.md) | worker (after E16) |
| E18 | [18-non-documents-and-tag-restraint.md](18-non-documents-and-tag-restraint.md) | worker (after E8) |

Each chapter has: Goal, contract, paired TDD loops (Red, Green, Refactor), Verification (with the `gh` commands or the local drain command), and Out of scope. Remote CI is the authoritative gate when Actions minutes exist; while they are exhausted (owner decision 2026-10-28) the full local CI is the gate. The proof for each chapter is in the ledger.
