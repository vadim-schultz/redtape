---
name: "Chapter 9 — Centred search and sort removal"
overview: "Replace the small search box and sort controls with a centred, raised, rounded search bar with a round arrow button, and make best-first ordering a fixed server-side default."
id: C9
depends_on:
  - C7
  - C12
touches:
  - apps/web/src/features/documents/
  - apps/web/src/components/data-display/ListSearchBox.tsx
  - apps/web/src/services/listQuery/
  - apps/web/src/theme/semantic-tokens/
  - apps/web/src/i18n/fallback/
  - apps/api/app/features/candidates/
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: pin-default-order
    content: "Characterise the API's no-sort ordering and pin it to the combined score."
    status: pending
  - id: search-hero
    content: "Add the SearchHero component: centred, raised, rounded, with a round arrow button."
    status: pending
  - id: remove-sort
    content: "Remove the sort control and sort plumbing from the documents page and stop sending sort parameters."
    status: pending
  - id: tokens-copy
    content: "Add the raised-shadow semantic token and clean up unused sort i18n keys."
    status: pending
  - id: tests
    content: "Add component, state, URL and request-contract tests and update the existing documents tests."
    status: pending
---

# Chapter 9 — Centred search and sort removal

**Repo:** `redtape` (`apps/web`, one API ordering fix)
**Depends on:** [Chapter 7](07-web-locale-foundation.md), [Chapter 12](12-combined-ranking-score.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Make search the visual centre of `/documents`: a bold, raised, rounded bar in the middle of the page with a round submit button, and no sort controls. Results are always best-first, so the server, not the UI, owns that rule.

## Design decisions

- **Pin the default order first (open seam O6).** The two code paths disagree: `candidates/repository/public_order.py` documents confidence-first ordering, while `candidates/list_query.py` (about lines 54–64) documents completeness-first when no sort is sent, and the UI today sends an explicit `sort_by=confidence&sort_order=desc` only when the user picks a non-default sort. Write a characterisation test of what `GET /api/v1/candidates` returns with no sort, then make the server default the **combined score** from chapter 12 (relevance blended with confidence when `q` is present, confidence alone when browsing, with the existing deterministic tie-breaks) in one place, deleting the disagreeing branch. The UI then sends no sort parameters. Removing the control before this is pinned could silently change the order users see (invariant 10).
- **`SearchHero`** (new, in `features/documents/components/SearchHeroView/`, about 3 props: `value`, `onSubmit`, `label`): horizontally centred in the panel, `maxW` about 640 px, larger input (`size="lg"`), fully rounded (`borderRadius="full"`), raised (`shadow="raised"`), the submit control a round `IconButton` (`rounded="full"`) with a right arrow (`LuArrowRight` from the existing `react-icons` set) placed at the input's end via an input group, `aria-label` from `documents.search_submit`. `<form role="search">`, draft-until-submit behaviour copied from `ListSearchBox` (typing does not fetch), an empty submit clears `q`, and the input has `dir="auto"` so mixed-language queries render correctly. Layout works at phone width with a 16 px gutter and at German and Russian text lengths.
- **`ListSearchBox`** (`components/data-display/`) is shared: check its other consumers first. If it is used elsewhere, leave it and add `SearchHero` beside it; if the documents page is its only consumer, replace it and remove the old component.
- **`shadow.raised`**: new semantic token under `src/theme/semantic-tokens/` with light and dark values (`mode()` helper as the others), no hardcoded colours in components.
- **Remove sorting from the page**: delete `DocumentSortControl.tsx`; remove `DOCUMENT_SORT_KEYS` (`features/documents/types/index.ts`), `DEFAULT_SORT` and the `setSort` handling in `hooks/useDocumentListState.ts`; stop passing `sort_by`/`sort_order` from `services/listQuery/params.ts` for this page. Stale `sort_by`/`sort_order` URL parameters are ignored and dropped on the next navigation. The shared list-query helpers keep sort support if other pages (admin lists) use it; this page just never sets it.
- **Copy:** remove the unused keys (`documents.sort_*`) from `en.json` and `de.json` (the locale parity test from chapter 7 enforces that no locale keeps them); reuse `documents.search_label`, `search_placeholder`, `search_submit`.
- Category chips stay directly under the bar; `filter[category]` as CSV is unchanged (`documentsApi.test.ts` and `DocumentsListPage.browse.test.tsx` pin it).
- Respect `apps/web/CLAUDE.md`: about 100 lines per file, about 3 props, about 5 lines per function; moves and renames first, logic in a separate commit.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/candidates/repository/public_order.py`, `list_query.py` | Consume chapter 12's combined-score default; remove the disagreeing no-sort branch (one place). |
| `apps/api/tests/test_candidates_public_api.py` (or a new ordering test) | Characterise and pin the no-sort order. |
| `apps/web/src/features/documents/components/SearchHeroView/` | `SearchHero.tsx`, `index.ts`, test. |
| `apps/web/src/features/documents/components/DocumentsListView/DocumentsListView.tsx`, `DocumentListControls.tsx` | Replace the controls row. |
| `apps/web/src/features/documents/components/DocumentsListView/DocumentSortControl.tsx` | Delete. |
| `apps/web/src/features/documents/hooks/useDocumentListState.ts`, `types/index.ts` | Remove sort state and keys. |
| `apps/web/src/services/listQuery/params.ts`, `url.ts` | Do not emit sort for this page; ignore stale sort params. |
| `apps/web/src/theme/semantic-tokens/` | `shadow.raised`. |
| `apps/web/src/i18n/fallback/en.json`, `de.json` | Remove `documents.sort_*`. |
| `apps/web/src/features/documents/**/*.test.tsx`, `hooks/useDocumentListState.test.tsx` | Update and add tests. |

## Red tests

### Happy path

- `api · no sort_by returns the combined-score order` (pins the default: relevance and confidence with `q`, confidence alone when browsing; fails first on the code path that disagrees).
- `SearchHero · submits on button click and Enter and sets q` and `typing alone does not fetch`.
- `SearchHero · is a search landmark with a labelled round submit button` and the input has `dir="auto"`.
- `DocumentsListPage · renders the hero and category chips and no sort control`.
- `documents request · sends no sort_by or sort_order and still sends filter[category] as CSV`.
- `list state · stale sort_by and sort_order URL params are ignored and dropped`.

### Negative path

- `SearchHero · an empty or whitespace submit clears q instead of searching for a blank`.
- `SearchHero · a very long query is passed through unchanged for the server to cap` (no client truncation surprises).
- `DocumentsListPage · there is no element with the sort select or direction button role`.
- `theme · the raised token has light and dark values` (no missing mode).
- `i18n parity · removed sort keys are gone from every locale file`.

## Green

1. Pin the API default with the characterisation and fix test.
2. Add the token and `SearchHero`; swap it into the view.
3. Remove sort plumbing and keys; update the tests.
4. Check desktop and phone width in the browser, `de` and a forced `ru` locale.

## Refactor gate

- No dead sort code remains on the page (`grep` for `sort_by`, `DocumentSortControl`, `DOCUMENT_SORT_KEYS` in `features/documents`).
- `SearchHero` has a typed props interface, no inline styles beyond tokens, no nested anchors or interactive elements.
- Architecture test still passes (no service imports in components, no inline query keys).
- The API default ordering exists in exactly one place.

## Verification

```bash
cd apps/api && uv run pytest tests/test_candidates_public_api.py tests/test_candidates_browse.py
cd ../web
npm test -- src/features/documents src/services
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Run the app (`npm run dev` with the API) and record screenshots before and after (desktop and mobile; `de` and `ru`) in [../run-ledger.md](../run-ledger.md), together with the pinned ordering result.

## Out of scope

Similarity or search-mode display (chapter 10), any hybrid retrieval, new languages, right-to-left layout, the global header or menu.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/search-hero-no-sort
```

```text
test(api): characterise and pin the default candidate ordering
refactor(web): move documents list controls behind SearchHero seam
feat(web): centred raised search bar without sort controls
```
