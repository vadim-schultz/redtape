---
name: Codebase audit remediation — Architecture
overview: "Post-merge review of the codebase-audit suite: close verified runtime seams, finish slipped refactors, and record the remaining audit gates honestly."
isProject: false
---

# Codebase audit remediation — Architecture

**Parent suite:** [codebase-audit](../codebase-audit/00-audit-report.md)  
**Baseline:** `main` at `95a3615`, merged by [PR #364](https://github.com/vadim-schultz/redtape/pull/364)  
**Follow-up rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Ledger:** [run-ledger.md](run-ledger.md)

## 1. Purpose

The parent audit implementation is substantially present on `main`, but a second static review found
runtime seams, incomplete refactors, and release evidence that the parent ledger never recorded. This
suite is a bounded follow-up. It does not reopen the parent audit's 25 chapters.

The suite is behaviour-preserving except for two correctness fixes:

- an emit-batch uniqueness race must not erase earlier successful inserts;
- `worker drain --max-tasks 0` must be rejected instead of silently becoming the default.

## 2. Verified findings

| ID | Severity | Finding | Evidence |
| --- | --- | --- | --- |
| R1 | High | `SuggestionService._insert()` calls a full session rollback after `IntegrityError`; a later idempotency race can erase earlier inserts in the same emit batch. | [`service.py`](../../apps/api/app/features/suggestions/service.py), [`repository.py`](../../apps/api/app/features/suggestions/repository.py) |
| R2 | Medium | The two discovery-admin drill-down pages pass bare loading text without `role="status"`. | [`DiscoveryDocumentPage.tsx`](../../apps/web/src/features/discovery-admin/containers/DiscoveryDocumentPage.tsx), [`DiscoveryPipelinePage.tsx`](../../apps/web/src/features/discovery-admin/containers/DiscoveryPipelinePage.tsx) |
| R3 | Medium | `max_tasks=max_tasks or None` converts an explicit CLI zero to the default claim size. | [`worker/commands.py`](../../apps/discovery-ingest/discovery_ingest/cli/worker/commands.py), [`test_ingest_operations_contract.py`](../../apps/discovery-ingest/tests/test_ingest_operations_contract.py) |
| R4 | Low | The feature-local `CompletenessChips` tree remains beside the shared tree. | [`components/data-display/CompletenessChips`](../../apps/web/src/components/data-display/CompletenessChips), [`features/candidates/components/CompletenessChips`](../../apps/web/src/features/candidates/components/CompletenessChips) |
| R5 | Low | `sectionPrefetch.ts` duplicates the query keys, functions, and artifact timing options defined by section hooks. | [`sectionPrefetch.ts`](../../apps/web/src/features/discovery-admin/containers/sectionPrefetch.ts), [`useAdminQuery.ts`](../../apps/web/src/features/discovery-admin/hooks/useAdminQuery.ts) |
| R6 | Low | T3 exceptions and the parent run ledger remain open or stale, so the audit cannot be signed off from repository evidence. | [`eslint.config.js`](../../apps/web/eslint.config.js), [`test_architecture.py`](../../apps/api/tests/test_architecture.py), [parent ledger](../codebase-audit/run-ledger.md) |
| R7 | Medium, operational | The C8 cleanup script is present but production cleanup and the endpoint smoke check remain operator-gated. | [`remove_leaked_fixture_jurisdictions.py`](../../apps/api/scripts/remove_leaked_fixture_jurisdictions.py), [`start.sh`](../../apps/api/scripts/start.sh) |

## 3. Refactoring gate

The review applied the refactoring skill to the containing entities, not only the changed lines.

| Containing entity | Smell | Required outcome |
| --- | --- | --- |
| `DiscoveryDocumentPage`, `DiscoveryPipelinePage` | Repeated loading presentation | Use the existing `LoadingNote` through `QueryBoundary`; do not add a page abstraction. |
| `sectionPrefetch.ts` and secondary query hooks | Duplicated query configuration | One typed `queryOptions` factory per resource, reused by both hook and prefetch. |
| `SuggestionService._insert` and suggestion persistence | Error path owns the wrong transaction boundary | Scope the uniqueness attempt to a savepoint or equivalent nested transaction. |
| `worker_drain` | Boundary coercion hides invalid input | Preserve zero and let explicit policy validation reject it. |
| `lifespan.py`, `worker/run.py` | Small duplicated constants | Reuse the existing shared constants; do not create one-line wrappers. |

No further extraction is justified for the linear catalogue ingest loop or the two artifact section
variants: each has one concern and only two variants.

## 4. Target state

- API emit batches preserve prior successful rows when one insert loses a uniqueness race.
- Discovery-admin page loading is announced to assistive technology.
- Omitted `--max-tasks` retains its existing default; explicit zero exits with `EXIT_USAGE`.
- Secondary query options have one source of truth.
- Only the shared `CompletenessChips` tree remains.
- The remediation ledger records test evidence, refactor outcomes, and operator-owned C8 status.

## 5. Scope

### In scope

- The R1, R2, and R3 correctness fixes and their regression tests.
- The R4 and R5 behaviour-preserving refactors.
- A post-implementation review report and honest remediation ledger.
- An operator handoff for C8; no production write is performed by code chapters.

### Out of scope

- Re-running the complete parent audit.
- Automatic production deletion or wiring C8 cleanup into startup.
- The remaining `SuggestionRead` ORM allow-list and Litestar hubs.
- The `DocumentService` locale data clump.
- URL sanitisation outside the already-reviewed admin path.
- The intentional TagSupport contract drift.

