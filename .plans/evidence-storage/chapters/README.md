# Evidence storage — chapters

One executable plan per chapter. Order, dependencies and gates: [../01-rollout.md](../01-rollout.md).

| # | File | Layer |
| --- | --- | --- |
| 1 | [01-object-store-port-and-settings.md](01-object-store-port-and-settings.md) | backend |
| 2 | [02-s3-adapter-and-minio.md](02-s3-adapter-and-minio.md) | backend + compose |
| 3 | [03-evidence-model-migration.md](03-evidence-model-migration.md) | model + migration |
| 4 | [04-evidence-service.md](04-evidence-service.md) | backend |
| 5 | [05-evidence-upload-endpoint.md](05-evidence-upload-endpoint.md) | backend |
| 6 | [06-evidence-read-endpoint.md](06-evidence-read-endpoint.md) | backend |
| 7 | [07-web-evidence-viewer.md](07-web-evidence-viewer.md) | frontend + i18n |
| 8 | [08-r2-runbook-and-provisioning.md](08-r2-runbook-and-provisioning.md) | docs + ops |
| 9 | [09-docs-sync.md](09-docs-sync.md) | docs |

Each chapter has: Goal, Design decisions, Files, Red tests (paired), Green, Refactor gate,
Verification, Out of scope, Git workflow.
