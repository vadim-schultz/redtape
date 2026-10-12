---
name: Discovery layer — Rollout
overview: "Twenty-three chapters: staging, admin pipeline API/UI, COS skills, ingest, emit, crawler adapter, docs. Loop branch feat/plans-discovery-layer."
isProject: false
---

# Discovery layer — Rollout

**Architecture:** [00-architecture.md](00-architecture.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/) · **Ledger:** [run-ledger.md](run-ledger.md)

**Loop branch:** `feat/plans-discovery-layer`  
**Release branch:** `main`

---

## The three invariants

1. **Staging is not canonical.**
2. **Each chapter ships with `./ci.sh` green.**
3. **Workers never import `app.db`.**

## Execution order (chief of staff)

1. [chapters/01-staging-migration-lineage.md](chapters/01-staging-migration-lineage.md)
2. [chapters/02-admin-discovery-api.md](chapters/02-admin-discovery-api.md)
3. [chapters/03-task-auto-enqueue-claim.md](chapters/03-task-auto-enqueue-claim.md)
4. [chapters/04-admin-shell-email-gate.md](chapters/04-admin-shell-email-gate.md)
5. [chapters/05-crawler-targets-table.md](chapters/05-crawler-targets-table.md)
6. [chapters/06-pipeline-drilldown.md](chapters/06-pipeline-drilldown.md)
7. [chapters/07-emit-preview-panel.md](chapters/07-emit-preview-panel.md)
8. [chapters/08-cos-govdata-skill.md](chapters/08-cos-govdata-skill.md)
9. [chapters/09-cos-pvog-skill.md](chapters/09-cos-pvog-skill.md)
10. [chapters/10-cos-fim-skill.md](chapters/10-cos-fim-skill.md)
11. [chapters/11-cos-leika-skill.md](chapters/11-cos-leika-skill.md)
12. [chapters/12-govdata-ozg-ingest.md](chapters/12-govdata-ozg-ingest.md)
13. [chapters/13-pvog-ingest-cli.md](chapters/13-pvog-ingest-cli.md)
14. [chapters/14-catalogue-task-fanout.md](chapters/14-catalogue-task-fanout.md)
15. [chapters/15-discovery-entity-dedup.md](chapters/15-discovery-entity-dedup.md)
16. [chapters/16-discovery-claim-evidence.md](chapters/16-discovery-claim-evidence.md)
17. [chapters/17-fim-leika-enrich.md](chapters/17-fim-leika-enrich.md)
18. [chapters/18-emit-suggestions.md](chapters/18-emit-suggestions.md)
19. [chapters/19-coverage-metrics.md](chapters/19-coverage-metrics.md)
20. [chapters/20-crawler-frontier-adapter.md](chapters/20-crawler-frontier-adapter.md)
21. [chapters/21-llm-extract-flag.md](chapters/21-llm-extract-flag.md)
22. [chapters/22-orchestration-runbook.md](chapters/22-orchestration-runbook.md)
23. [chapters/23-docs-sync.md](chapters/23-docs-sync.md)

## Chapters

| # | Chapter | Plan | Status |
| --- | --- | --- | --- |
| 1–23 | See execution order | [chapters/](chapters/) | planned |

## Per-chapter gate

```bash
cd apps/api && python -m pytest tests/<file>.py
cd ../.. && ./ci.sh
```

**Branches:** `feat/discovery-layer-<slug>` from loop branch; PR into `feat/plans-discovery-layer`.

## Orchestration

Merge this suite to `main`, then chief of staff on `.plans/discovery-layer/`. See [docs/operations/loops/discovery-layer.md](../../docs/operations/loops/discovery-layer.md).
