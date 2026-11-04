---
name: Codebase audit remediation — Post-implementation review
overview: "Static review of the merged codebase-audit result at main 95a3615, with verified findings and the follow-up suite that owns them."
isProject: false
---

# Post-implementation review — codebase audit at `95a3615`

**Merge:** [PR #364](https://github.com/vadim-schultz/redtape/pull/364) → `main`  
**Review mode:** read-only static review; no production data mutation and no code changes in this report.

## Verdict

The parent audit substantially shipped across API, discovery-ingest, web, and lint/type gates. It is
not fully closed: one high-consequence transaction seam, two medium correctness issues, two slipped
web refactors, stale T3/G2 evidence, and the operator-owned C8 check remain.

## Findings

| ID | Severity | Finding | Owner |
| --- | --- | --- | --- |
| R1 | High | Full session rollback after a suggestion `IntegrityError` can erase earlier inserts in an emit batch. | Chapter 1 |
| R2 | Medium | Document and pipeline drill-down loading is not announced with `role="status"`. | Chapter 1 |
| R3 | Medium | Explicit `--max-tasks 0` becomes the default claim size through `or None`. | Chapter 1 |
| R4 | Low | Feature-local and shared `CompletenessChips` trees both remain. | Chapter 2 |
| R5 | Low | Prefetch and section hooks duplicate TanStack query configuration. | Chapter 2 |
| R6 | Low | Parent T3/G2 allow-lists and run ledger are not fully closed with evidence. | Chapter 3 |
| R7 | Medium, operational | C8 production fixture cleanup is not verified and must remain operator-gated. | Chapter 3 / operator |

## Refactor-gate report

- `DiscoveryDocumentPage` and `DiscoveryPipelinePage`: duplicated loading presentation found; use
  `LoadingNote` through the existing `QueryBoundary`.
- `sectionPrefetch.ts` and secondary query hooks: duplicated query configuration found; extract
  shared typed factories.
- `SuggestionService._insert`: transaction-boundary smell found; scope the uniqueness attempt to a
  savepoint.
- `worker_drain`: invalid-input coercion found; preserve the value and use the existing policy guard.
- Catalogue ingest and the two artifact section variants: no extraction needed; each remains one
  concern with only two variants.

## Verification limits

This review did not execute the full local CI suite or mutate production. Chapter PRs must add
red/green evidence and the chief of staff must record the final `./ci.sh` result in
[run-ledger.md](run-ledger.md). The GitHub Actions API was not independently queried during the
review because the repository API request was forbidden.

