---
name: "Chapter 8 — Matrix page"
overview: "A /matrix route showing life situations as rows and domains as columns with per-cell counts; cells, whole rows (all documents for a situation), whole columns (all documents for a domain) and the grand total link to the filtered documents list; nav entry added."
todos:
  - id: page
    content: "MatrixPage container with query status handling"
    status: completed
  - id: grid
    content: "MatrixGrid, MatrixCell, row and column header links with distinct-document totals, corner all-documents link"
    status: completed
  - id: route
    content: "Lazy route /matrix and nav link"
    status: completed
  - id: mobile
    content: "Narrow-viewport layout: situation list with domain counts, no horizontal scroll trap"
    status: completed
isProject: false
---

# Chapter 8 — Matrix page

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/matrix-page` · **Status:** done

**Depends on:** [5](05-matrix-endpoint.md), [6](06-web-taxonomy-client.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`/matrix` lets a user start from "I'm moving" or "my car": a grid of situations × domains with document
counts. Four selections, all plain links into the documents list:

| Click | Goes to | Shows |
| --- | --- | --- |
| Cell | `/documents?domain=D&situation=S` | Documents in that domain **and** situation |
| Row header (situation) | `/documents?situation=S` | **All** documents for that life situation |
| Column header (domain) | `/documents?domain=D` | **All** documents for that domain |
| Corner ("all documents") | `/documents` | Everything in scope |

Empty cells are visually quiet and inert. Row and column headers print their distinct-document total
from the API. Reachable from the app shell nav.

## Design decisions

**Data composition in the container.** `MatrixPage` runs three queries (domains, situations, matrix)
and passes plain arrays to `MatrixView`; presentational components receive props only, matching
[DocumentsListView](../../../apps/web/src/features/documents/components/documents-list/DocumentsListView.tsx).

**Cell lookup by key.** Build a `Map<"domainCode|situationCode", count>` once; cells read from it.
Missing key = empty cell; never render a zero as a link.

**Axes come from the matrix response, names from the taxonomy lists.** Rows are the situations named in
`matrix.situations`, columns the domains in `matrix.domains` (so terms with no documents in scope are
hidden, D11), ordered by the taxonomy lists' `sort_order`, labelled with the lists' resolved `name` and
`icon`. Header totals are `AxisTotal.count` as delivered — **never summed from cells** (D10); a test
fixes a row whose total is smaller than the sum of its cells.

**Headers are links, not buttons.** `MatrixRowHeader` and `MatrixColumnHeader` render a router `Link`
with the name and the total, with a visible focus ring and an accessible name such as
"Moving house, 7 documents". Links keep middle-click, copy-link and back-button behavior. The corner
cell is the all-documents link and shows `matrix.total`. Link targets are built by one pure
`buildDocumentsHref({domain?, situation?})` util (added in chapter 6, shared with the tag badges of chapter 9), so code encoding lives in one place.

**Wide grid, narrow viewport.** 13 columns do not fit a phone. Below the `md` breakpoint render the
transpose: one `AppCard` per situation whose **title links to all documents for that situation**
(with its total), listing its non-empty domains as cell links with counts. A domain-wide selection on
phones comes through the domain chips on the list (chapter 7) and a compact domain link row above the
cards. Same data,
different composition component (`MatrixGrid` vs `MatrixSituationCards`), selected with Chakra's
responsive display, not JS measurement. Alternative: horizontal scroll — rejected as poor mobile UX.

**Cell visual.** Count intensity uses a small step scale from theme tokens (subtle → wine), not raw hex;
the count is always printed so color is never the only signal (accessibility).

**Component tree (one per file):**
`containers/MatrixPage` → `components/matrix/{MatrixView, MatrixGrid, MatrixCorner, MatrixColumnHeader, MatrixRowHeader, MatrixRow, MatrixCell, MatrixSituationCards, MatrixDomainLinks, MatrixEmpty}`.
Link building uses `buildDocumentsHref` from chapter 6.

**Routing and nav.** Add a lazy route in [routes.tsx](../../../apps/web/src/app/routes.tsx) with a
skeleton fallback, and a nav item in [AppLayout](../../../apps/web/src/components/layout/AppLayout.tsx)
using existing key `nav.*` plus a new `nav.matrix` key (added here to both bundles if not already
present from chapter 6).

## Files

**Add** — `apps/web/src/features/taxonomy/containers/MatrixPage.tsx`,
`apps/web/src/features/taxonomy/components/matrix/*.tsx` with tests, `MatrixSkeleton.tsx`.

**Edit** — `apps/web/src/app/routes.tsx`, `apps/web/src/components/layout/AppLayout.tsx` (+ its test),
translation bundles for `nav.matrix`.

## Red tests

| Test | Asserts |
| --- | --- |
| `MatrixCell · non-empty cell links to the filtered list` | `href` contains both codes |
| `MatrixRowHeader · links to all documents for the situation` | `href` is `/documents?situation=S`, no domain param |
| `MatrixColumnHeader · links to all documents for the domain` | `href` is `/documents?domain=D`, no situation param |
| `MatrixCorner · links to /documents and shows the grand total` | No params, `matrix.total` printed |
| `MatrixRowHeader · shows the API total, not the sum of its cells` | Fixture where total < sum of cells |
| `MatrixGrid · hides situations and domains absent from the matrix response` | Scope-specific axes (D11) |
| `MatrixSituationCards · card title links to all documents for the situation` | Mobile row selection |
| `MatrixCell · empty cell renders no link and no count` | Negative |
| `MatrixGrid · renders one header per domain and one row per situation` | Structure |
| `MatrixView · builds cell lookup so unrelated pairs stay empty` | No cross-talk |
| `MatrixPage · matrix query error shows QueryError, no grid` | Negative |
| `MatrixPage · loading shows the skeleton` | State |
| `MatrixPage · no tagged documents shows MatrixEmpty` | Empty state |
| `MatrixSituationCards · lists only non-empty domains per situation` | Mobile composition |
| `routes · /matrix resolves and unknown paths still show NotFoundView` | Regression |
| `AppLayout · nav includes a matrix link` | Discoverability |

## Green

1. `MatrixCell`, then `MatrixRow`/`MatrixColumnHeader`, then `MatrixGrid`; each test-first.
2. `MatrixSituationCards`; `MatrixView` chooses composition via responsive display.
3. Container, route, nav link.

## Refactor gate

- `MatrixView` only composes; lookup building lives in a pure `buildCellIndex(cells)` util with its own
  test.
- No component over ~100 LOC; `MatrixGrid` stays a layout shell.
- No nested ternaries for loading/error/empty: use one `MatrixQueryStatus` like
  [DocumentsListQueryStatus](../../../apps/web/src/features/documents/components/documents-list/DocumentsListQueryStatus.tsx).

## Verification

```bash
cd apps/web
npm run test -- src/features/taxonomy src/app src/components/layout
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: dev server, `/matrix` in light and dark, resize below `md`. Click a cell, a row header, a column
header and the corner; confirm each list is filtered as in the table above and the chips match (needs
chapter 7).

## Out of scope

Graph/tree display per situation, jurisdiction switching UI beyond the existing location bar, counts
animation.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-page
```

```text
test(web): describe matrix grid, cells and states

feat(web): add matrix page linking situations and domains to filtered documents
```
