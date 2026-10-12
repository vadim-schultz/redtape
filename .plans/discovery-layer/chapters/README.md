# Discovery layer — chapters

One executable plan per chapter. Order, dependencies and gates: [../01-rollout.md](../01-rollout.md). Data and API contract: [../02-staging-model-and-api.md](../02-staging-model-and-api.md).

| # | File | Layer |
| --- | --- | --- |
| 1 | [01-staging-migration-lineage.md](01-staging-migration-lineage.md) | model + migration |
| 2 | [02-admin-discovery-api.md](02-admin-discovery-api.md) | backend |
| 3 | [03-task-auto-enqueue-claim.md](03-task-auto-enqueue-claim.md) | backend |
| 4 | [04-admin-shell-email-gate.md](04-admin-shell-email-gate.md) | web |
| 5 | [05-crawler-targets-table.md](05-crawler-targets-table.md) | web |
| 6 | [06-pipeline-drilldown.md](06-pipeline-drilldown.md) | web |
| 7 | [07-emit-preview-panel.md](07-emit-preview-panel.md) | web + API |
| 8 | [08-cos-govdata-skill.md](08-cos-govdata-skill.md) | docs |
| 9 | [09-cos-pvog-skill.md](09-cos-pvog-skill.md) | docs |
| 10 | [10-cos-fim-skill.md](10-cos-fim-skill.md) | docs |
| 11 | [11-cos-leika-skill.md](11-cos-leika-skill.md) | docs |
| 12 | [12-govdata-ozg-ingest.md](12-govdata-ozg-ingest.md) | ingest |
| 13 | [13-pvog-ingest-cli.md](13-pvog-ingest-cli.md) | ingest |
| 14 | [14-catalogue-task-fanout.md](14-catalogue-task-fanout.md) | backend |
| 15 | [15-discovery-entity-dedup.md](15-discovery-entity-dedup.md) | backend |
| 16 | [16-discovery-claim-evidence.md](16-discovery-claim-evidence.md) | deferred |
| 17 | [17-fim-leika-enrich.md](17-fim-leika-enrich.md) | ingest |
| 18 | [18-emit-suggestions.md](18-emit-suggestions.md) | backend |
| 19 | [19-coverage-metrics.md](19-coverage-metrics.md) | backend + web |
| 20 | [20-crawler-frontier-adapter.md](20-crawler-frontier-adapter.md) | deferred |
| 21 | [21-llm-extract-flag.md](21-llm-extract-flag.md) | deferred |
| 22 | [22-orchestration-runbook.md](22-orchestration-runbook.md) | docs + ops |
| 23 | [23-docs-sync.md](23-docs-sync.md) | docs |

Each **in-loop** chapter has: Goal, Design decisions, Files, Red tests (paired), Green, Refactor gate,
Verification, Out of scope, Git workflow.
