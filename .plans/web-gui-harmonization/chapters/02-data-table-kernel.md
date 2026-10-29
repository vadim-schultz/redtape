---
name: "Chapter 2 — DataTable and Chakra pagination kernel"
overview: "Introduce one typed, state-aware DataTable and a Chakra compound pagination control for all later admin migrations."
todos:
  - id: table-types
    content: "Define typed columns, row navigation, state slots, and pagination contracts."
    status: pending
  - id: table
    content: "Implement the shared DataTable and Chakra pagination behavior."
    status: pending
  - id: tests
    content: "Add paired tests for capabilities, state views, and pagination."
    status: pending
isProject: false
---

# Chapter 2 — DataTable and Chakra pagination kernel

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-gui-harmonization-data-table` · **Status:** planned  
**Depends on:** [01-visual-foundation.md](01-visual-foundation.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-web-gui-harmonization` · **Release branch:** `main`

## Goal

`apps/web/src/components/data-display/DataTable/` provides the single table presentation primitive:
typed columns, explicit sort/filter capabilities, row navigation, semantic cells, state slots,
horizontal overflow, and Chakra pagination. It remains domain-agnostic.

## Design decisions

- Parent hooks own query state; the table emits typed sort/filter/page events.
- `canSort` and `filter` are explicit column capabilities. Display columns get no accidental control.
- Loading, error, empty, populated, and refreshing states are opt-in slots so existing callers can
  migrate incrementally.
- Use `Pagination.Root` and related Chakra compound components. Hide the control when there is one
  page, disable impossible navigation, and preserve the current range text.
- Preserve previous rows during a refetch and expose `aria-busy`; do not replace the table with a
  blank skeleton for every query transition.

## Files

**Add**

- `apps/web/src/components/data-display/DataTable/DataTable.tsx`
- `DataTableHeader.tsx`, `DataTableRow.tsx`, `DataTableStateView.tsx`
- `types.ts`, `sorting.ts`, `pagination.ts`, `index.ts`
- `apps/web/src/components/data-display/Pagination.tsx`
- colocated unit/component tests

**Edit**

- shared feedback and table semantic-token imports as required by the kernel
- component barrels only where architecture conventions require them

**Do not edit**

- discovery feature services or API query parameters
- resource-specific columns
- public document card behavior

## Red tests

| Test | Asserts |
| --- | --- |
| `DataTable renders headers and cells from typed columns` | A row and its cell renderers appear with real table semantics. |
| `DataTable toggles a sortable column from ascending to descending` | The parent receives the expected typed sort events. |
| `DataTable omits controls for a display-only column` | Negative: a column without sort/filter capability cannot emit a sort or filter event. |
| `DataTable shows explicit error and empty states` | Error and empty slots are visible and do not render stale row content. |
| `Pagination renders page navigation for multiple pages` | Chakra pagination exposes current page and navigation controls. |
| `Pagination hides and blocks navigation for a single or invalid page` | Negative: no unnecessary controls appear and invalid callbacks are not invoked. |

Confirm both paths in each slice fail for the intended missing behavior before implementation.

## Green

1. Add types and sorting/pagination pure helpers.
2. Implement the table shell and semantic header/row/cell treatment using chapter 1 tokens.
3. Add state resolution and refreshing behavior.
4. Add the Chakra pagination compound component.
5. Run narrow tests after each extraction, especially after separating header, row, and state views.

## Refactor gate

Audit the complete DataTable module, including all state branches, pagination calculations, row
navigation, and public props. Extract only named units that own real behavior; remove duplicated
sort/pagination math; confirm no boolean prop hides two unrelated table modes. Report the outcome and
rerun the narrow suite after every extraction.

## Verification

```bash
cd apps/web
npm run test -- src/components/data-display/DataTable src/components/data-display/Pagination
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Out of scope

- API sorting/filtering
- feature-specific filters or columns
- migration of existing admin tables
- coverage layout

## Git workflow

```bash
git checkout feat/plans-web-gui-harmonization && git pull
git checkout -b feat/web-gui-harmonization-data-table
```

Suggested commits:

```text
test(web): define DataTable capability and pagination states
feat(web): add shared DataTable kernel
```

Open the chapter PR into `feat/plans-web-gui-harmonization`.

