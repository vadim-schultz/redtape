# Candidate view — chapters

One executable plan per chapter. Order, dependencies and gates: [../01-rollout.md](../01-rollout.md). Decisions: [../gaps-and-decisions.md](../gaps-and-decisions.md). Ledger: [../run-ledger.md](../run-ledger.md).

| # | File | Layer |
| --- | --- | --- |
| 1 | [01-capture-requeue.md](01-capture-requeue.md) | API (machine route) + ingest CLI |
| 2 | [02-completeness-read-model.md](02-completeness-read-model.md) | API |
| 3 | [03-public-candidate-api.md](03-public-candidate-api.md) | API |
| 4 | [04-admin-list-contract.md](04-admin-list-contract.md) | API |
| 5 | [05-web-candidate-list.md](05-web-candidate-list.md) | web |
| 6 | [06-web-candidate-detail.md](06-web-candidate-detail.md) | web |
| 7 | [07-flow-diagram.md](07-flow-diagram.md) | web |
| 8 | [08-admin-documents-table.md](08-admin-documents-table.md) | web |
| 9 | [09-catalogue-vs-coverage.md](09-catalogue-vs-coverage.md) | API + web |
| 10 | [10-docs-and-release.md](10-docs-and-release.md) | docs |
| 11 | [11-manual-curation-tool.md](11-manual-curation-tool.md) | ingest (executes after chapter 2) |

Each chapter has: Goal, contract or design decisions, files to edit and not to edit, paired TDD loops (red tests with a happy and a negative case, green, refactor gate), Verification with the gate commands, commits, and Out of scope. The screenshot collection (LR1, after chapter 1) and the showcase curation (LR2, after chapters 2, 3 and 11) are not chapters: the chief of staff runs [../02-live-runs.md](../02-live-runs.md).
