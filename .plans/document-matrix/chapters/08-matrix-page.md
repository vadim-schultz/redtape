---
name: "Chapter 8 — Matrix page"
overview: "A /matrix route showing life situations as rows and domains as columns with per-cell document counts; each non-empty cell links to the filtered documents list; nav entry added."
todos:
  - id: page
    content: "MatrixPage container with query status handling"
    status: pending
  - id: grid
    content: "MatrixGrid, MatrixCell, axis headers as separate components"
    status: pending
  - id: route
    content: "Lazy route /matrix and nav link"
    status: pending
  - id: mobile
    content: "Narrow-viewport layout: situation list with domain counts, no horizontal scroll trap"
    status: pending
isProject: false
---

# Chapter 8 — Matrix page

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/matrix-page` · **Status:** planned

**Depends on:** [5](05-matrix-endpoint.md), [6](06-web-taxonomy-client.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`/matrix` lets a user start from "I'm moving" or "my car": a grid of 18 situations × 13 domains with
document counts, empty cells visually quiet and inert, non-empty cells linking to
`/documents?domain=<d>&situation=<s>`. Reachable from the app shell nav.

## Design decisions

**Data composition in the container.** `MatrixPage` runs three queries (domains, situations, matrix)
and passes plain arrays to `MatrixView`; presentational components receive props only, matching
[DocumentsListView](../../../apps/web/src/features/documents/components/documents-list/DocumentsListView.tsx).

**Cell lookup by key.** Build a `Map<"domainSlug|situationSlug", count>` once; cells read from it.
Missing key = empty cell; never render a zero as a link.

**Wide grid, narrow viewport.** 13 columns do not fit a phone. Below the `md` breakpoint render the
transpose: one `AppCard` per situation listing its non-empty domains as links with counts. Same data,
different composition component (`MatrixGrid` vs `MatrixSituationCards`), selected with Chakra's
responsive display, not JS measurement. Alternative: horizontal scroll — rejected as poor mobile UX.

**Cell visual.** Count intensity uses a small step scale from theme tokens (subtle → wine), not raw hex;
the count is always printed so color is never the only signal (accessibility).

**Component tree (one per file):**
`containers/MatrixPage` → `components/matrix/{MatrixView, MatrixGrid, MatrixColumnHeader, MatrixRow, MatrixCell, MatrixSituationCards, MatrixEmpty}`.

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
| `MatrixCell · non-empty cell links to the filtered list` | `href` contains both slugs |
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

Manual: dev server, `/matrix` in light and dark, resize below `md`, click a cell, confirm the list is
pre-filtered and chips reflect it (needs chapter 7).

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
