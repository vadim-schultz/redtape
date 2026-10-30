# Admin tables: list contract, components, and release smoke checks

How the discovery admin lists (`/admin/discovery/documents`, `tasks`, `catalogue`) and tables
(coverage, mentions, edges, stored pages) share one table language. Plan and decisions:
[`.plans/web-gui-harmonization/`](../../.plans/web-gui-harmonization/00-architecture.md). Route
surface: [discovery-layer.md](discovery-layer.md#web-admin-route-surface).

## List query contract

Server-paged admin lists accept the same query shape. Source of truth: `ListQuerySpec` per resource
in `apps/api/app/shared/list_query/` and the typed specs in `apps/web/src/services/listQuery/`.

| Parameter | Meaning |
| --- | --- |
| `offset`, `limit` | Page window. `offset >= 0`, `limit` 1 to 100, default 20. |
| `sort_by`, `sort_order` | Allowlisted sort field and `asc` or `desc`. `sort_order` needs `sort_by`. Ties always break on stable keys. |
| `q` | Free-text search, 1 to 200 characters, on the fields the resource declares. |
| `filter[field]` | Allowlisted exact or bounded filter. |

- Responses are `{items, total, offset, limit}`. `total` describes the complete filtered result.
- An unknown sort field, unknown `filter[...]` key, or invalid value is rejected with `422` and
  `{status_code, detail: "Invalid list query", extra: [{key, message, source: "query"}]}`.
  Validation runs before the repository, so a rejected query never reads or writes partial data.
- Changing search, filter, or sort resets the offset to the first page.
- The URL is the canonical state of the three paged admin lists, so a link restores the same view.
- Mentions, edges, and stored pages are one record's complete sets from unpaged, fixed-order
  endpoints; they declare no sort or filter and are not paged. Coverage tables are static summaries.
- The toolbar sits in the table header, not above the table: search and "clear filters" are a header
  slot of `DiscoveryDataTable`, and active filters appear as removable chips. The documents table
  also has a Ready quick filter (`filter[complete]=yes`, the five completeness flags of the
  [public candidate view](candidate-view.md)).
- A cell that holds a long title is bounded: `DataTableColumn.maxWidth` clips it with an ellipsis,
  and a tooltip shows the whole text on hover and on keyboard focus. The documents Title column
  and the tasks target column use it.
- The catalogue list sorts by `title` and filters by pipeline `stage`. Its summary chips (total,
  source, stage) filter the table and count the whole catalogue, not the filtered rows.
- Public `/documents` and `/suggestions` are not part of this contract. They show at most the first
  20 rows by design (decision D11 in the plan).

## Components

| Component | Responsibility |
| --- | --- |
| `components/data-display/DataTable` | The only table presentation. Typed columns, header sort and filter controls, row links, loading, empty, error, refreshing, and refetch-failed states. It holds no query state: the parent owns it and the table emits typed events. |
| `components/data-display/Pagination` | Chakra pagination of an offset window; hidden for a single page. |
| `components/data-display/SectionCard` | The raised, static section shell with an optional title and toolbar. |
| `features/discovery-admin/components/columns/` | Domain column builders (`xColumns(useLocale())`). They declare columns only; they do not render tables. |
| `features/discovery-admin/components/DiscoveryDataTable` | The paged-list adapter: shell, total, empty state, loading, and paging for a server-paged list. |
| `features/discovery-admin/components/coverage/` | Coverage groups as static tables in titled section shells. |
| `hooks/useListQueryState` | URL-backed list state and its setters. |

Architecture tests keep this split: no table primitive outside `DataTable`, no feature
component importing a feature service, no inline query keys.

## Accessibility contract

- A table is named (`label`) and every column header has text. Display columns carry no
  sort or filter control; sortable headers set `aria-sort` and are operated by a button named
  after the column.
- A column filter is a button named by its capability label, with a popover dialog of the same name.
  `Escape` discards the draft; `Apply` and `Clear` commit.
- The scroll container of a wide table is a keyboard-focusable group named `<table>, scrollable`.
- Long values (URLs, excerpts, conditions) wrap inside `LongText` instead of truncating, so the
  full value stays readable and selectable at narrow widths.
- Numeric columns declare `align: "end"`; the header and cells align together.
- Loading is announced as a `status`; a failed refresh keeps the previous rows with an alert and
  a retry; a first-load failure shows the error and retry inside the table shell.
- Pagination is a named navigation; the current page has `aria-current="page"`, and a disabled
  edge control is skipped by the keyboard.

The automated checks live in `DataTable.a11y.test.tsx`, `Pagination.test.tsx`,
`adminStates.accessibility.test.tsx`, and the helper `src/test/tableAccessibility.ts`. They run in
jsdom and cannot judge layout, colour, or visible focus.

## Release smoke checks

Run these in a browser against a stack with an allowlisted admin account before releasing the
harmonized GUI. Status: **not yet performed**. The automated suites cannot cover them, and the
chapter implementation had no browser. Record the result next to the release PR.

- [ ] Keyboard only: tab through the sort and filter controls, a row link, the scroll group, and
      pagination on `documents`, `tasks`, and `catalogue`; every control shows a visible focus ring
      and has a sensible spoken name.
- [ ] Light and dark mode: canvas, raised table and section shells, borders, shadows, and the
      filter popover surface stay legible and consistent.
- [ ] Narrow viewport (about 360 px): wide tables scroll horizontally, nothing is clipped, and the
      scroll group can be scrolled with the arrow keys.
- [ ] Long values: a long task URL, mention excerpt, and external ID stay inspectable.
- [ ] Empty groups and API errors: stop the API or filter to no results; each state shows
      explicit feedback and a working retry.
- [ ] Background refetch: leave a list, return to the tab, and confirm rows stay visible while the
      table is busy; a failed refetch shows the alert with the previous rows.
- [ ] Filters and sort: apply, remove, and clear filters; the page resets to the first one and the
      URL restores the view after a reload.
- [ ] `/admin/discovery/documents` shows no non-functional expand chevron beside the count.
- [ ] Coverage numbers are right-aligned and readable in both colour modes.
- [ ] Document detail (mentions, dependencies, stored artifacts) and pipeline detail use the same
      section shell.
