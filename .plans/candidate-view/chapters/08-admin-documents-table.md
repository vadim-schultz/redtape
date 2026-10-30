---
name: "Chapter 8 — Admin documents table"
overview: "Bring /admin/discovery/documents up to the DataTable contract: search and clear in the table header, every column sortable and filterable, a Readiness column with a Ready quick filter, and a bounded Title column whose full text is in a Chakra tooltip."
todos:
  - id: column-width
    content: "DataTableColumn gains an optional maxWidth; TruncatedText clips and shows the full text in a Tooltip (first in the app)"
    status: pending
  - id: header-toolbar
    content: "DiscoveryDataTable passes a toolbar to SectionCard; search and clear filters move into it; the standalone filter bar goes"
    status: pending
  - id: column-capabilities
    content: "Every candidate column declares canSort and filter where chapter 4 allowlists it; Readiness column and Ready quick filter"
    status: pending
  - id: tasks-target
    content: "The tasks target column uses the same bounded cell"
    status: pending
isProject: false
---

# Chapter 8 — Admin documents table

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/candidate-view-admin-table` · **Status:** planned  
**Depends on:** [04-admin-list-contract.md](04-admin-list-contract.md) (sort and filter keys, response flags), [05-web-candidate-list.md](05-web-candidate-list.md) (`CompletenessChips`) · **Architecture:** [../00-architecture.md](../00-architecture.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

`/admin/discovery/documents` meets the contract of [web-gui-harmonization](../../web-gui-harmonization/00-architecture.md): each column is sortable and filterable where the API allows it, the toolbar is part of the table header, long titles no longer force sideways scrolling, and an admin can see and filter **which candidates are ready** with the same five flags the public pages use.

Today (read from the code on 2026-10-30):

- `DiscoveryDocumentFilters` is a free-standing `HStack` above the table card; `DiscoveryDocumentsPage` renders it before `DiscoveryDocumentsTable`.
- `candidateColumns` declares `canSort` on title, mentions and first seen only, and **no column declares `filter`**, so the kernel's header popovers and removable filter chips never appear (the toolbar filters are invisible to `activeFilters`).
- The Title cell is a bare router `Link`; `DataTableColumn` has no width or truncation option; the only wrapping helper is `LongText` (`min-width: 12rem`, wraps anywhere).
- The web app has no tooltip anywhere.

## Design decisions

- **Toolbar in the header.** `SectionCard` already has a `toolbar` slot beside its title (`SectionCardProps.toolbar`). `DiscoveryDataTable` gains an optional `toolbar` prop and passes it through; the documents page puts `ListSearch` and `ClearFilters` there. The `min_mentions`, `role` and `source` selects leave the toolbar: they become column filters (below). Other tables (catalogue, tasks) are untouched except for the target cell.
- **Column capabilities** (keys from chapter 4):

  | Column | Sort | Filter |
  | --- | --- | --- |
  | Title | `title` | `contains` (free text, `q`) is the search box, not a column filter; the column only sorts |
  | Jurisdiction | `jurisdiction` | `eq` on `jurisdiction` (free text) |
  | Roles | `roles` | `eq` select `role` (required, form, issued) |
  | Mentions | `mentions` | `gte` on `min_mentions` (select 1, 2, 5, 10) |
  | Status | `status` | `eq` select `status` (staged, emitted) |
  | Source | none (display) | `eq` select `source` |
  | Readiness | `completeness` | `eq` select `complete` (yes / no) |
  | First seen | `created_at` | none (a date range filter is out of scope) |

  Where a column has no meaningful filter the plan says so instead of inventing one; "each column sortable and filterable" is met where the data supports it, and the gap is recorded in the architecture doc and the ledger, not hidden.
- **Readiness column.** Renders `CompletenessChips` (built in chapter 5; same component as the public cards) from the five flags in the admin list item. A **Ready** quick filter button in the toolbar sets `filter[complete]=yes` and shows as an active filter chip; clearing it is the chip's remove control.
- **Bounded cells.** `DataTableColumn` gets `maxWidth?: string` (a Chakra size token or CSS length); the cell wrapper applies it with `overflow: hidden`. New `TruncatedText` (`components/data-display/TruncatedText.tsx`): clips with an ellipsis at the column's width, keeps the content a link when the parent renders a link, and wraps the text in a Chakra `Tooltip` showing the full text. The Title column uses `maxWidth="28rem"`; the tasks `target` column swaps `LongText` for it with `maxWidth="24rem"`. Mention excerpts keep `LongText` (they are meant to be read in full).
- **Tooltip.** Chakra v3.37 ships `Tooltip` parts; add the standard snippet `components/ui/tooltip.tsx` (portal, positioner, `showArrow`). The tooltip trigger is the clipped text itself; keyboard users get the full text through `aria-label`-free, visible focus on the link plus the tooltip on focus (Chakra opens on focus). The text is also the accessible name of the link, so screen readers read it whole regardless of clipping.
- **No change** to the kernel's sorting or filtering semantics, to the URL shape, or to how the API is called beyond the new keys (`candidateListQuery.ts` spec gains the keys of chapter 4).

## Files

**Edit**

- `apps/web/src/components/data-display/DataTable/types.ts` (`maxWidth` on `DataTableColumn`) and `DataTableRow.tsx` (apply it to the cell)
- `apps/web/src/features/discovery-admin/components/DiscoveryDataTable.tsx` (`toolbar` prop)
- `apps/web/src/features/discovery-admin/containers/DiscoveryDocumentsPage.tsx`, `components/DiscoveryDocumentsTable.tsx`, `components/DiscoveryDocumentFilters.tsx` (reduced to search, clear and the Ready button), `components/documentFilterFields.ts` (removed or reduced to the option lists reused by the columns)
- `apps/web/src/features/discovery-admin/components/columns/candidateColumns.tsx`, `candidateRows.ts`, `columns/cells/` (a `CandidateReadinessCell`)
- `apps/web/src/features/discovery-admin/components/columns/taskColumns.tsx` (target cell)
- `apps/web/src/features/discovery-admin/services/candidateListQuery.ts` and `types/` (`CandidateSortKey`, `CandidateFilterKey`, flags on `DiscoveryCandidate`)
- `apps/web/src/i18n/fallback/en.json` and `de.json` (`discovery_admin.documents.col_readiness`, `ready_filter`, filter labels)

**Create**

- `apps/web/src/components/ui/tooltip.tsx`, `apps/web/src/components/data-display/TruncatedText.tsx` (+ test)

**Do not edit**

- API code (chapter 4 owns it), the kernel's pagination, sorting and filter logic, the guards, coverage and catalogue pages (chapter 9)

## Red tests

| Test | Asserts |
| --- | --- |
| `documents page renders search and clear inside the table card header` | The search box and the clear button are descendants of the section card's header, not siblings above it. |
| `every sortable candidate column sets sort_by and sort_order on header click` | Title, Jurisdiction, Roles, Mentions, Status, Readiness and First seen each produce the chapter 4 key; `aria-sort` follows. |
| `column filter applies and shows a removable chip` | Choosing `staged` in the Status header filter sends `filter[status]=staged`, shows the chip, and removing it clears the request. |
| `ready quick filter sets filter complete` | The Ready button sends `filter[complete]=yes`, resets the offset to 0, and shows as an active filter. |
| `readiness column shows five flags per row` | A row with `has_screenshot=false` shows that chip unset with an accessible name saying so. |
| `long title is clipped and the tooltip carries the full title` | A 200-character title renders with the column's max width; focusing or hovering reveals the full text; the link name is the full title. |
| `tasks target uses the bounded cell` | A long target URL is clipped and available in full through the tooltip. |
| Negative: `unknown filter value in the url falls back` | `?filter[status]=bogus` is dropped to the default by the existing parser and no request carries it. |
| Negative: `no row text is lost when the table is narrow` | At a narrow container the table still scrolls horizontally (kernel behaviour) and every cell remains in the DOM. |
| Negative: `header toolbar is absent from other tables` | The catalogue and tasks tables render without a toolbar prop and without extra header markup. |

Write and run these before implementing; confirm they fail for the stated reason.

## Green

1. Add `maxWidth` to the column type and the row cell; add the tooltip snippet and `TruncatedText` with their tests.
2. Add the `toolbar` prop to `DiscoveryDataTable` and move search, clear and the Ready button into it.
3. Declare sort and filter on the candidate columns; add the readiness cell; extend the list-query spec and types with the chapter 4 keys.
4. Swap the tasks target cell.
5. Add the en and de strings.

## Refactor gate

Audit the containing entities: `candidateColumns.tsx` (one factory returning columns; keep each cell in `columns/cells/`, no inline JSX over a few lines), `DiscoveryDataTable.tsx` (props stay at three groups; the new `toolbar` joins `copy`), `DiscoveryDocumentFilters.tsx` (now small; delete it if it only forwards), and any duplicated option lists between `documentFilterFields.ts` and `filterOptions.ts` (rule of three: extract only if three places repeat). Report what was extracted or "audited, nothing needed".

## Verification

```bash
cd apps/web
npm run test -- src/components/data-display src/features/discovery-admin
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

Manual (recorded for the smoke in chapter 10): open `/admin/discovery/documents`, confirm the header toolbar, filter by Status and Ready, hover and keyboard-focus a long title, resize to a narrow width.

## Commits

`test(web): define the documents table header toolbar, filters and bounded title`, `feat(web): add TruncatedText with a tooltip and column max width`, `feat(web): bring the admin documents table to the DataTable contract`.

## Out of scope

Date-range filters, column visibility menus, saving table views, changing the kernel's URL format, the public list (chapter 5), catalogue and coverage (chapter 9).
