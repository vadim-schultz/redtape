# Discovery admin flow consolidation - chapters

Read the chapters in dependency order. The batches in the [rollout](../01-rollout.md) show which chapters may run at the same time.

## Chapter list

| ID | Chapter | Depends on | Chapter file |
| --- | --- | --- | --- |
| C1 | Flow aggregates | none | [01-flow-aggregates.md](01-flow-aggregates.md) |
| C2 | Flag-only language menu | none | [02-flag-language-menu.md](02-flag-language-menu.md) |
| C3 | Flow translation and failures | C1 | [03-flow-translation-and-failures.md](03-flow-translation-and-failures.md) |
| C4 | Flow page and probe | C1, C3 | [04-flow-page-and-probe.md](04-flow-page-and-probe.md) |
| C5 | Frontend view removal | C4 | [05-frontend-view-removal.md](05-frontend-view-removal.md) |
| C6 | Backend endpoint removal | C3, C5 | [06-backend-endpoint-removal.md](06-backend-endpoint-removal.md) |
| C7 | Docs and runbook | C6 | [07-docs-and-runbook.md](07-docs-and-runbook.md) |
| C8 | Release | C1, C2, C3, C4, C5, C6, C7 | [08-release.md](08-release.md) |

## Dependency graph

```text
C1 -> C3
C1 -> C4
C2 -> C8
C3 -> C4
C3 -> C6
C4 -> C5
C5 -> C6
C6 -> C7
C7 -> C8
```
