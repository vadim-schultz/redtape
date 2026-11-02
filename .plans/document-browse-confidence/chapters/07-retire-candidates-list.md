---
name: "Chapter 7 — Retire the candidates list"
overview: "Redirect /candidates to /documents, delete the now-duplicate candidates list page and its components, keep the candidate item page, and point its Back button at the documents list."
todos:
  - id: redirect
    content: "/candidates redirects to /documents; /candidates/:id stays"
    status: pending
  - id: delete-list
    content: "Delete CandidatesListPage, CandidatesListView, CandidatesBanner and list-only hooks, specs and utils"
    status: pending
  - id: back-button
    content: "CandidateBackButton returns to /documents with its URL state"
    status: pending
  - id: menu-link
    content: "Remove the /candidates menu link"
    status: pending
  - id: tests-i18n
    content: "Update route, menu and i18n tests; trim unused candidates.* keys"
    status: pending
isProject: false
---

# Chapter 7 — Retire the candidates list

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/document-browse-confidence-retire-candidates-list` · **Status:** planned
**Depends on:** Chapters 3 and 6 · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

After chapter 3 `/documents` is the candidate list with search, sort and chips, so the second list at `/candidates` is a duplicate. One list remains; the candidate **item** page (flow diagram, evidence, screenshot) stays at `/candidates/:id`, where document cards link (D10). Paths under `apps/web/src/`.

## Design

- `app/routes.tsx`: `/candidates` becomes `{ path: "/candidates", element: <Navigate to="/documents" replace /> }`; remove the lazy `CandidatesListPage` and the `CandidatesListSkeleton` import. `/candidates/:id` unchanged.
- Delete under `features/candidates/`: `containers/CandidatesListPage.tsx` (+ `.test.tsx`, `.filters.test.tsx`), `components/CandidatesListView/` (all files, including `CandidatesSearch`, `TermChipRow`, `CompleteOnlySwitch`, `FilterActions`, `AxisFilter`), `components/CandidatesBanner/`, `hooks/useCandidateListState*`, `hooks/useCandidatesQuery.ts`, `utils/hasActiveFilters*`. Keep `services/candidateListQuery.ts` and `services/candidatesApi.ts::fetchCandidates` only if chapter 3's documents service imports them; otherwise move what is shared into `features/documents/services/` and delete the rest. `components/CandidateTagBadges/` and `CandidateListCard` are deleted if chapter 3 did not reuse them (check imports; do not leave dead files).
- `components/CandidateDetailView/CandidateBackButton.tsx`: it restores the list URL when the visitor came from the list (`state.fromList`). Point it at `/documents` and have `DocumentCard` pass `state={{ fromList: true }}` (as `CandidateListCard` does today) so the back link restores `?q=…&sort_by=…&domain=…`.
- `components/layout/menu/DocumentsMenuRow.tsx`: remove the `/candidates` link (the "Browse documents" link to `/documents` is the single entry). Update `DocumentsMenuRow.test.tsx` counts and the candidates-row assertions.
- i18n: remove the `candidates.*` keys that only the deleted list used (title, subtitle, banner_*, filter and search labels, sort labels, empty-state texts) from `i18n/fallback/en.json`, `de.json` and `apps/api/scripts/seed_data/translations/en.json`, `de.json` together. `fallback.test.ts` has an explicit `candidates.*` key list: update that list in the same commit. Keep keys the item page still reads (`candidates.from_source`, detail strings, checklist, flow). Verify each key with a grep over `src/` before removing.
- `app/queryKeys.ts`: remove `candidates.list` if nothing uses it.

## Tests

Happy path:
- `App.test.tsx`: `/candidates` redirects to `/documents` (list page renders); `/candidates/:id` still renders the item page.
- `CandidateBackButton.test.tsx`: coming from the documents list with `?q=ausweis&domain=housing`, Back goes to `/documents?q=ausweis&domain=housing`; direct visit goes to `/documents`.
- `DocumentCard.test.tsx`: the card link targets `/candidates/:id` and carries `fromList` state.

Negative path:
- `/candidates?domain=x` redirects to `/documents` without crashing (the old params are dropped, not misread).
- No remaining import of a deleted module: `tsc --noEmit` and `architecture.test.ts` pass; `rg "CandidatesListView|CandidatesBanner|useCandidateListState" apps/web/src` returns nothing.
- `fallback.test.ts` stays green: web fallback equals the API seed for `en` and `de`, and no removed key is still referenced (`rg` per key).

## Verification

```bash
cd apps/web && npx vitest run src/app src/features/candidates src/features/documents src/components/layout src/i18n
./ci.sh
```

## Refactor gate

Scan `routes.tsx`, `CandidateBackButton.tsx`, `DocumentsMenuRow.tsx` and whatever was moved from `candidates` to `documents`. Remove dead code rather than leaving it dormant (Speculative Generality / Dead Code).

## Commits

- `refactor(web): redirect /candidates to /documents and delete the duplicate list`
- `chore(web): drop the unused candidates list strings`

## Out of scope

The candidate item page and its API; unifying the item URL under `/documents/:id` (seam in the gaps doc); the candidate admin pages.
