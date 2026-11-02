---
name: "Chapter 5 — Two-stage chips"
overview: "Make the eight life-area chips real selections in swiss red that match every document of the area, and give the situation chips inside an area a lighter red, so the filter has a coarse and a fine stage."
todos:
  - id: filter-state
    content: "useDocumentFilters: group param with per-group exclusivity against situations"
    status: pending
  - id: expansion
    content: "situationCodes(): groups expand to their situation codes for the request"
    status: pending
  - id: tokens
    content: "Semantic tokens for the lighter sub-selection red, WCAG-asserted"
    status: pending
  - id: chip-tone
    content: "FilterChip tone prop: group, sub, plain"
    status: pending
  - id: tests
    content: "State, expansion, colour and deep-link tests"
    status: pending
isProject: false
---

# Chapter 5 — Two-stage chips

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/document-browse-confidence-two-stage-chips` · **Status:** planned
**Depends on:** Chapter 3 ([03-documents-on-candidates.md](03-documents-on-candidates.md)) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4–5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

Today the eight life-area chips are navigation only (`pressed={false}` always, `SituationFilterView.tsx`), so a selected life-situation chip never shows the satisfying red of a selected domain chip. After this chapter:

- selecting a **life area** (one of the 8 groups) turns its chip bright swiss red and selects **all** documents of every situation in that area, with no finer granularity;
- selecting a **situation inside** an area narrows the filter; its chip is a **lighter red**;
- domain chips keep their current red.

## Design

Paths under `apps/web/src/`.

### State — `features/documents/hooks/useDocumentFilters.ts`

- New repeated URL param `group` (axis `"group"` beside `domain`, `situation`).
- Exclusivity per group, enforced in the toggle functions (pure helper in `features/documents/utils/groupSelection.ts`, easier to test than the hook):
  - `toggleGroup(code)`: if the group is selected → remove it; otherwise add it **and remove every selected situation whose `group_code` is that group**.
  - `toggleSituation(code)`: add or remove it; when adding, remove the situation's group from `group`.
  - The helper takes the situations list (`GroupedTerm[]`) to resolve membership.
- Every toggle deletes `offset` (chapter 3).
- Returned shape gains `groups` and `toggleGroup`; `clear` wipes `group` too, and "Clear filters" appears when `domains + groups + situations > 0`.

### Request expansion — `features/documents/utils/situationCodes.ts`

`situationCodes(filters, situations): string[]` = de-duplicated union of selected situation codes and every situation code whose `group_code` is in `filters.groups`. Unknown group codes and a group with no loaded situations contribute nothing. `useDocumentsListQuery` sends this list as `filter[situation]`; the query key carries the raw `groups` and `situations` (stable) rather than the expanded list.

### Chips — `components/DocumentFiltersView/`

- `FilterChip.tsx` gains `tone?: "plain" | "group" | "sub"` (default `plain`, i.e. current behaviour used by domains). `pressed` + tone decide the look:

  | State | Look |
  | --- | --- |
  | `plain` pressed | `colorPalette="primary"`, `variant="solid"` (unchanged) |
  | `group` pressed | same swiss red as above: `primary.500` solid |
  | `group`, not pressed, but it has sub-selections | `variant="outline"`, primary (a hint) |
  | `sub` pressed | new lighter-red tokens (below) |
  | any, not pressed | `colorPalette="gray"`, `variant="subtle"` (unchanged) |

- Theme: add semantic tokens in `theme/semantic-tokens/` (for example `chip.sub.selected.bg|fg|border`), light and dark, with `bg` between `primary.100` and `primary.300` in light mode and the matching dark-mode tone. `theme/theme.test.ts` asserts WCAG AA contrast (4.5:1) of `fg` on `bg` in both modes using its existing helper, and that `bg` differs from `primary.500` (so the two stages are distinguishable).
- `SituationFilterView.tsx`: group chips use `tone="group"` with `pressed = filters.groups.includes(code)` and call `toggleGroup`; clicking also expands the group (selecting expands, deselecting leaves the expansion as is). Situation chips of the expanded group use `tone="sub"`. When a group is group-wide selected, its situation chips render not pressed (the group already includes them); clicking one narrows to it (the helper swaps group for situation). The existing derived expansion for deep links (`touchedGroup`) is kept and now also expands a `group=` deep link.
- Props stay within three: `SituationFilterView` takes `groups`, `situations`, `filters`.

## Tests

Happy path:
- `groupSelection.test.ts`: selecting a group removes its situations; selecting a situation removes its group; selecting situations in two groups keeps both; deselecting works both ways.
- `situationCodes.test.ts`: a group expands to exactly its situations; group plus an unrelated situation unions without duplicates.
- `SituationFilterView.test.tsx`: group chip pressed shows swiss red (computed colour equals `primary.500`), sub chip pressed shows the lighter token; `?group=work-career` deep link renders the group pressed and expanded; the request carries all codes of the group.
- `theme.test.ts`: contrast of the new tokens in light and dark.

Negative path:
- `?group=nope` (unknown group) is ignored: no chip pressed, no codes sent, no crash.
- A group whose situations have not loaded sends nothing and renders without error.
- Selecting a sub-situation of a group-wide selected group leaves exactly one state (situation selected, group not), never both.

## Verification

```bash
cd apps/web && npx vitest run src/features/documents src/theme
./ci.sh
```

## Refactor gate

Scan `useDocumentFilters.ts` (Mutable Data / Long Function once a third axis exists — extract the pure helper), `FilterChip.tsx` (Primitive Obsession on `tone`: a typed union, not strings), `SituationFilterView.tsx` and `DocumentFilters.tsx`.

## Commits

- `feat(web): select life areas as filters and expand them to their situations`
- `feat(web): two-stage red for life-area and life-situation chips`

## Out of scope

A `group` filter in the API (D9); changing domain chip colours; an "all of this area" chip inside the expanded row.
