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
| E10 | [10-robots-rules-fix.md](10-robots-rules-fix.md) | worker (executes first) |

Each chapter has: Goal, contract, paired TDD loops (Red, Green, Refactor), Verification (with the `gh` commands or the local drain command), and Out of scope. Local checks are best effort; the chapter PR's GitHub Actions checks are the authoritative gate.
