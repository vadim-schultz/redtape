---
name: "Chapter 4 — Discovery admin table migration"
overview: "Migrate catalogue, documents, tasks, and mentions to the shared DataTable with consistent shells, state handling, typography, and pagination."
todos:
  - id: columns
    content: "Create typed column builders for catalogue, candidates, tasks, and mentions."
    status: pending
  - id: migration
    content: "Replace direct table markup and bespoke list state wiring with DataTable consumers."
    status: pending
  - id: tests
    content: "Add paired migration tests for populated and rejected/empty/error states."
    status: pending
isProject: false
---

# Chapter 4 — Discovery admin table migration

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-gui-harmonization-admin-tables` · **Status:** planned  
**Depends on:** [02-data-table-kernel.md](02-data-table-kernel.md), [03-list-contract-and-adapters.md](03-list-contract-and-adapters.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-web-gui-harmonization` · **Release branch:** `main`

## Goal

The discovery admin catalogue, documents, tasks, mentions, and row-comparable nested
pipeline/detail lists use the same table shell, typography, row behavior, state slots, and
pagination. Feature column builders retain all domain-specific labels, links, badges, and
formatting. Narrative timelines and structured emit previews remain their own semantic surfaces.

## Design decisions

- Keep containers responsible for query orchestration and presentational components responsible for
  columns/table state.
- Use one column builder per resource rather than a single configuration object with resource
  conditionals.
- Keep row links for candidates and catalogue rows where they already exist. Nested buttons/links
  remain keyboard-operable.
- Use response `total` for counts. Tasks must not report only the current page length.
- Replace the feature-local pagination control with the shared Chakra pagination contract.
- Keep feature-specific loading skeletons or empty icons only when they add clear domain meaning;
  otherwise use shared DataTable state slots.

## Files

**Add**

- `apps/web/src/features/discovery-admin/components/columns/catalogueColumns.tsx`
- `candidateColumns.tsx`, `taskColumns.tsx`, `mentionColumns.tsx`
- feature table adapters or view folders required by `apps/web/CLAUDE.md`
- colocated tests

**Edit**

- `DiscoveryDocumentsTable.tsx`
- `DiscoveryTasksTable.tsx`
- `CatalogueServicesTable.tsx`
- `DocumentMentionsTable.tsx`
- row-comparable pipeline/detail list components such as artifact, edge, tag/support, or snapshot
  lists identified by the implementation audit
- `DiscoveryDocumentsQueryStatus.tsx`
- `DiscoveryTasksQueryStatus.tsx`
- discovery catalogue/documents/tasks containers and hooks
- `PaginationControl.tsx` only to remove duplication or provide a compatibility adapter during the
  migration

**Do not edit**

- coverage layout (chapter 5)
- the API contract beyond consuming chapter 3
- public document/suggestion cards

## Red tests

| Test | Asserts |
| --- | --- |
| `discovery documents render typed columns inside the shared table shell` | Candidate title links, jurisdiction, roles, counts, status, and time render with shared semantics. |
| `discovery tasks render response rows and total count` | Task cells and the full response total appear; page length is not used as the total. |
| `catalogue, mentions, and nested admin lists use the shared table contract` | Comparable admin records expose the same state and table-shell structure while preserving feature cells; timelines/previews remain intentionally non-table. |
| `admin tables render an explicit empty or error state without stale rows` | Negative: empty/error responses do not leave stale rows or blank content. |
| `admin table rejects an unsupported column interaction` | Negative: a display-only column cannot send an undeclared sort/filter key. |

Confirm the existing direct-table behavior and new contract failures before changing production code.

## Green

1. Build each typed column list with existing labels and formatters.
2. Replace direct table markup with `DataTable` while keeping the current route/query inputs.
3. Move count/error/loading/empty handling into shared slots or a thin feature adapter.
4. Add task pagination and use the API total.
5. Remove obsolete duplication only after all four consumers are green.

## Refactor gate

Audit each column builder, all four table components, and both query-status wrappers. Count all
branches for state and row variants; extract a factory or named renderer when a table decision has
three or more paths. Remove one-line wrappers and data clumps. Rerun the narrow table suite after
each extraction and record the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin/components src/features/discovery-admin/containers
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Out of scope

- Coverage metric redesign
- New filter operators
- Public browse layout
- Pipeline timeline redesign

## Git workflow

```bash
git checkout feat/plans-web-gui-harmonization && git pull
git checkout -b feat/web-gui-harmonization-admin-tables
```

Suggested commits:

```text
test(web): define discovery admin DataTable consumers
feat(web): migrate discovery admin tables to shared DataTable
```

Open the chapter PR into `feat/plans-web-gui-harmonization`.

