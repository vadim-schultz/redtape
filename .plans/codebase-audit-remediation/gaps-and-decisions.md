---
name: Codebase audit remediation — Gaps and decisions
overview: "Scope boundaries, settled implementation choices, and deferred seams for the post-merge audit remediation."
isProject: false
---

# Codebase audit remediation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md) · **Ledger:** [run-ledger.md](run-ledger.md)

**Parent audit:** [codebase-audit](../codebase-audit/00-audit-report.md)

## Settled decisions

| ID | Decision | Consequence |
| --- | --- | --- |
| D1 | Use a savepoint or equivalent scoped rollback for suggestion insert races. | An `IntegrityError` rolls back only the contested insert; prior emit-batch inserts remain in the outer transaction. |
| D2 | Use `LoadingNote` through `QueryBoundary` on both discovery-admin drill-down pages. | Loading is announced consistently with the existing panel implementation. |
| D3 | Share one typed `queryOptions` factory between each section hook and `sectionPrefetch.ts`. | Query keys, fetch functions, and timing options cannot drift between prefetch and render. |
| D4 | Preserve `None` as the omitted CLI value and reject explicit `0`. | Existing defaults remain unchanged; invalid bounds exit with `EXIT_USAGE` before any claim request. |
| D5 | Keep C8 cleanup operator-owned. | No startup hook, workflow, or chapter runs `remove_leaked_fixture_jurisdictions.py --apply`. |
| D6 | Keep the follow-up suite separate from the historical parent audit. | Parent evidence remains auditable; new work gets its own branch and ledger. |

## Open decisions

| ID | Topic | Default handling | Owner | Next action |
| --- | --- | --- | --- | --- |
| O1 | Remaining T3 web/API exceptions | Record each permanent exception with rationale and owner; do not delete a baseline line without evidence. | API/web maintainers | Add the exact allow-list entry and evidence to the parent audit closeout. |
| O2 | `SuggestionRead.from_row` ORM import | Defer a mapper-port extraction until a suggestions chapter owns that boundary. | Suggestions/API maintainer | Create a dedicated layering chapter when the suggestions read boundary changes. |
| O3 | Litestar reached through shared list-query and locale hubs | Defer domain-error and boundary splitting to a dedicated layering chapter. | API architecture owner | Split the HTTP boundary when the next layering pass owns these hubs. |
| O4 | `DocumentService` locale data clump | Record as informational; do not expand this follow-up into a document-read redesign. | Documents/API maintainer | Reassess during a document-read redesign; no action in this suite. |
| O5 | `safeHttpUrl` at non-header link sites | Record as defence-in-depth risk; schedule separately unless a concrete unsafe payload is reproduced. | Web security owner | Add focused payload coverage before scheduling the shared link-site change. |
| O6 | Web `accepted` versus API `score` TagSupport drift | Keep the intentional contract gap visible; resolve with the owning tagging work. | Tagging owner | Reconcile the contract in the next tagging change. |
| O7 | Duplicate ingest error-detail constants | Consolidate only where the remediation chapter already touches the module; otherwise record the drift risk. | Discovery-ingest maintainer | Consolidate in the next ingest error-contract change. |

## Explicitly deferred risks

- A promotion uniqueness race may still need a separate 409 mapping if a reproducible path remains after
  the emit savepoint work.
- Partial GovData page ingest and partial enrich writes remain documented operational semantics.
- The parent audit's full chapter ledger is not retroactively fabricated. A remediation ledger can
  link evidence, but it cannot claim parent chapters that have no evidence.
- Production C8 status remains unknown until the operator records the dry-run, approved apply, and
  endpoint verification.

## Scope exclusions

No new product features, migrations beyond those already on `main`, dependency upgrades, workflow
changes, automatic production writes, mobile changes, or full re-audit.

