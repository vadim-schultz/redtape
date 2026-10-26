# Crawlers — chapters

One executable plan per chapter. Order, dependencies and gates: [../01-rollout.md](../01-rollout.md). Decisions: [../gaps-and-decisions.md](../gaps-and-decisions.md). Ledger: [../run-ledger.md](../run-ledger.md).

| # | File | Layer | Slice |
| --- | --- | --- | --- |
| 1 | [01-ingest-ci.md](01-ingest-ci.md) | CI | foundation |
| 2 | [02-fetcher-hardening.md](02-fetcher-hardening.md) | worker | foundation |
| 3 | [03-kind-filtered-claim.md](03-kind-filtered-claim.md) | API + worker + migration | foundation |
| 4 | [04-retry-and-backoff.md](04-retry-and-backoff.md) | API + worker + migration | foundation |
| 5 | [05-drain-throughput-and-queue-summary.md](05-drain-throughput-and-queue-summary.md) | API + CI workflow | foundation |
| 6 | [06-candidate-staging-model-and-api.md](06-candidate-staging-model-and-api.md) | model + migration + API | documents |
| 7 | [07-pvog-payload-harvester.md](07-pvog-payload-harvester.md) | worker + API | documents |
| 8 | [08-admin-queue-kinds-and-metrics.md](08-admin-queue-kinds-and-metrics.md) | API + frontend | documents |
| 9 | [09-menu-icon-row.md](09-menu-icon-row.md) | frontend | documents |
| 10 | [10-admin-documents-list.md](10-admin-documents-list.md) | API + frontend | documents |
| 11 | [11-candidate-emit.md](11-candidate-emit.md) | API + worker | documents |
| 12 | [12-fim-key-fix.md](12-fim-key-fix.md) | API + worker + probe | documents |
| 13 | [13-object-store-port-and-r2-adapter.md](13-object-store-port-and-r2-adapter.md) | API + CI workflow (Cloudflare R2) | storage |
| 14 | [14-artifact-model-and-api.md](14-artifact-model-and-api.md) | model + migration + API | storage |
| 15 | [15-cloudflare-render-and-snapshot.md](15-cloudflare-render-and-snapshot.md) | worker + CI workflow | storage |
| 16 | [16-admin-artifacts-panel.md](16-admin-artifacts-panel.md) | frontend | storage |
| 17 | [17-extractor-framework.md](17-extractor-framework.md) | worker | extraction |
| 18 | [18-first-page-extractor.md](18-first-page-extractor.md) (optional) | worker | extraction |
| 19 | [19-screenshot-capture.md](19-screenshot-capture.md) | worker | evidence |
| 20 | [20-admin-document-detail-and-evidence.md](20-admin-document-detail-and-evidence.md) | frontend | evidence |
| 21 | [21-docs-sync.md](21-docs-sync.md) | docs | wrap-up |
| 22 | [22-operator-manual-steps.md](22-operator-manual-steps.md) | docs + ops | wrap-up |
| 23 | [23-free-tier-guards.md](23-free-tier-guards.md) (executes between 14 and 15) | model + migration + API + worker client | storage |

Each chapter has: Goal, contract, paired TDD loops (Red, Green, Refactor), Verification (with the GitHub Actions `gh` commands), and Out of scope. Local checks are best-effort; the chapter PR's GitHub Actions checks are the authoritative gate.
