# Crawlers — Run ledger

**Loop branch:** `feat/crawlers`
**Release branch:** `main`

Update this ledger after every chapter implementation or documented operator verification. A chapter is not complete until its gate, its live gate (or the reason it is deferred), and its refactor outcome are recorded. Record GitHub Actions run IDs for every live gate.

| Chapter | Plan | Status | Verification | Refactor outcome | Live gate (run ID) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [Ingest CI](chapters/01-ingest-ci.md) | planned | | | | |
| 2 | [Fetcher hardening](chapters/02-fetcher-hardening.md) | planned | | | | |
| 3 | [Kind-filtered claim and enum groundwork](chapters/03-kind-filtered-claim.md) | planned | | | | |
| 4 | [Retry and backoff](chapters/04-retry-and-backoff.md) | planned | | | | |
| 5 | [Drain throughput and queue summary](chapters/05-drain-throughput-and-queue-summary.md) | planned | | | | |
| 6 | [Candidate staging model and API](chapters/06-candidate-staging-model-and-api.md) | planned | | | | |
| 7 | [PVOG payload harvester](chapters/07-pvog-payload-harvester.md) | planned | | | | |
| 8 | [Admin queue kinds and metrics](chapters/08-admin-queue-kinds-and-metrics.md) | planned | | | | |
| 9 | [Menu icon row](chapters/09-menu-icon-row.md) | planned | | | | |
| 10 | [Admin Documents list](chapters/10-admin-documents-list.md) | planned | | | | |
| 11 | [Candidate emit](chapters/11-candidate-emit.md) | planned | | | | |
| 12 | [FIM key fix](chapters/12-fim-key-fix.md) | planned | | | | |
| 13 | [Object store port and Supabase adapter](chapters/13-object-store-port-and-supabase-adapter.md) | planned | | | | |
| 14 | [Artifact model and API](chapters/14-artifact-model-and-api.md) | planned | | | | |
| 15 | [Snapshot on fetch](chapters/15-snapshot-on-fetch.md) | planned | | | | |
| 16 | [Admin Artifacts panel](chapters/16-admin-artifacts-panel.md) | planned | | | | |
| 17 | [Extractor framework and extract_page](chapters/17-extractor-framework.md) | planned | | | | |
| 18 | [First page extractor](chapters/18-first-page-extractor.md) | planned | | | | |
| 19 | [Screenshot capture](chapters/19-screenshot-capture.md) | planned | | | | |
| 20 | [Admin document detail and evidence](chapters/20-admin-document-detail-and-evidence.md) | planned | | | | |
| 21 | [Docs sync](chapters/21-docs-sync.md) | planned | | | | |
| 22 | [Operator manual steps](chapters/22-operator-manual-steps.md) | planned | | | | |

## Release checklist

- [ ] The ingest package has its own CI workflow and it is green (chapter 1).
- [ ] Redirects are followed and no longer recorded as success (chapter 2).
- [ ] The scheduled drain claims only kinds it handles, retries transient failures, and drains more than one batch with a known `remaining` (chapters 3–5).
- [ ] Document candidates exist with mentions and provenance, and the admin Documents screens show them (chapters 6, 7, 10).
- [ ] The navigation icons render in one unbroken row (chapter 9).
- [ ] One operator-driven candidate emit created pending `new_document` suggestions (chapter 11).
- [ ] FIM enrichment fires for GovData rows and produces claims (chapter 12).
- [ ] Object-store probe is green and snapshots appear as artifacts (chapters 13–16).
- [ ] At least one extractor produced candidates from live snapshots (chapters 17–18).
- [ ] A screenshot was captured and is visible in the admin (chapters 19–20).
- [ ] Operations docs and the loop doc are synchronized; evidence-storage and discovery-layer pointers are updated (chapter 21).
- [ ] The operator checklist is complete (chapter 22).
- [ ] Link/frontier crawling, freshness, LLM extraction, requirement emit, and a web voting UI remain out of scope.
- [ ] Release PR from `feat/crawlers` to `main` is ready.
