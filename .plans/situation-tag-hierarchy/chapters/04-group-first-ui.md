---
name: "Chapter 4 — Group-first browsing and confidence-ranked display"
overview: "Default situation filtering shows the 8 groups, not 18 codes; opening a group reveals its situations, and a selected situation reveals leaf-refinement chips only when the current results actually have any. Tag badges render confidence as a visual gradient instead of a flat badge, and selecting a situation sorts results by persisted confidence."
todos:
  - id: group-query
    content: "Add useLifeSituationGroupsQuery + taxonomyApi.listLifeSituationGroups + query key"
    status: pending
  - id: situation-filter-view
    content: "New SituationFilterView/ replacing the flat situation FilterGroup: group chips, expand to situation chips"
    status: pending
  - id: leaf-facet
    content: "Add DocumentService.available_leaf_codes() + expose on the list response; render as a third-level facet"
    status: pending
  - id: tag-confidence-type
    content: "Extend the frontend Term type with confidence; thread through DocumentTags/TagBadge"
    status: pending
  - id: badge-gradient
    content: "TagBadge renders opacity/variant from confidence instead of a flat badge"
    status: pending
  - id: sort-by-confidence
    content: "DocumentRepository.list_page() orders by max(confidence) across matched situation link rows when a situation filter is active"
    status: pending
  - id: tests
    content: "Component tests for group expand/collapse and non-empty-only facet rendering; repository ordering test"
isProject: false
---

# Chapter 4 — Group-first browsing and confidence-ranked display

**Repo:** `redtape` (`apps/web`, plus small `apps/api` read-model/ordering additions) · **Branch:** `feat/situation-tag-hierarchy-group-first-ui` · **Status:** planned

**Depends on:** Chapter 1 ([01-confidence-scoring-engine.md](01-confidence-scoring-engine.md)) — `TaggedTermRead.confidence`; Chapter 2 ([02-life-situation-groups.md](02-life-situation-groups.md)) — the group tier and `group_code`; Chapter 3 ([03-pvog-leaf-refinement.md](03-pvog-leaf-refinement.md)) — `pvog_leaf_code` on `document_life_situation` · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-hierarchy`

## Goal

Three UI changes, all reading data the first three chapters already persisted — this chapter adds no new scoring or taxonomy logic, only renders what exists:

1. The situation filter defaults to the 8 groups (`DocumentFiltersView/DocumentFilters.tsx` currently renders a flat 18-chip `FilterGroup` for situations); opening a group reveals its situation chips.
2. Once a situation is selected, a leaf-refinement facet appears **only when the current result set has at least one matching leaf code** — never an empty facet.
3. A document's tags (`DocumentTagsView/DocumentTags.tsx`, `TagBadge.tsx`) render their persisted confidence as a visual gradient instead of a flat badge, and selecting a situation sorts the document list by confidence.

## Design

### Backend additions (apps/api)

- `apps/api/app/features/documents/service.py::DocumentService`: add `available_leaf_codes(filters: DocumentFilters) -> list[str]` — distinct non-null `pvog_leaf_code` values on `document_life_situation` rows matching the current `situation_ids`/`jurisdiction_id` scope, empty list when zero or more than one situation is selected (the facet only makes sense once browsing is inside exactly one situation). Backed by a new `DocumentRepository.leaf_codes_in_scope()` query, same shape as the existing `_base_select()`/`_filter_by_terms()` helpers.
- `apps/api/app/schema/document/read.py::DocumentListResponse`: add `available_leaf_codes: list[str] = Field(default_factory=list)`, populated by `list_documents()` alongside the existing `items`/`total` — one round trip, no new endpoint.
- `apps/api/app/features/documents/repository.py::DocumentRepository.list_page()`/`_base_select()`: when `situation_ids` is non-empty, order by `max(document_life_situation.confidence)` across the matched rows, descending, before the existing `Document.slug.asc()` tiebreak; unchanged (slug order) when no situation filter is active. Documented as a pragmatic first choice, not validated against an alternative combination rule for multi-select — see `../gaps-and-decisions.md`'s open seam.

### Frontend additions (apps/web)

- `apps/web/src/features/taxonomy/hooks/useLifeSituationGroupsQuery.ts` (new, mirrors `useDomainsQuery`/`useLifeSituationsQuery`) + `taxonomyApi.ts::listLifeSituationGroups()` + a new key in `app/queryKeys.ts`.
- `apps/web/src/features/documents/hooks/useFilterTaxonomy.ts`: add `groups: Term[]` to `FilterTaxonomy`, from the new query, folded into the existing retry/error handling.
- New `apps/web/src/features/documents/components/DocumentsListView/DocumentFiltersView/SituationFilterView/` (replaces the plain `FilterGroup` call for situations in `DocumentFilters.tsx`; domains keep using `FilterGroup` as-is, unchanged):
  - `SituationFilterView.tsx` — owns which group is expanded (local state, one at a time); renders group chips via the existing `FilterChip`; renders the expanded group's situation chips (also `FilterChip`, reusing the existing component, not a new one) beneath it.
  - `LeafFacet.tsx` — renders only when `availableLeafCodes.length > 0`; one more row of `FilterChip`s, toggling a `leaf` query param the same way `buildDocumentsHref` already composes `domain`/`situation` params.
  - `index.ts` barrel exporting `SituationFilterView`.
  - Props stay within the ~3-prop convention: `SituationFilterView` takes `groups`, `situations`, `filters` (reusing the existing `DocumentFiltersState` shape — no new filter state, group expansion is pure UI navigation, not a filter dimension).
- `apps/web/src/features/documents/taxonomy/types.ts` (wherever `Term` is defined): add `TaggedTerm extends Term { confidence: number }`, used only by `DocumentTagsView` — `FilterGroup`/`FilterChip` keep using plain `Term` (the vocabulary itself has no confidence; only a specific document's tag does).
- `DocumentTagsView/DocumentTags.tsx`: props change from `domains: Term[]` / `lifeSituations: Term[]` to `TaggedTerm[]`, passing `confidence` through to `TagBadge`.
- `DocumentTagsView/TagBadge.tsx`: add a `confidence: number` prop; map it to Chakra's `opacity` (`0.5 + 0.5 * confidence`, so even a low-confidence tag stays legible, never vanishing) instead of the single fixed `variant="subtle"` every badge uses today. No binary "accepted" styling anywhere — a continuous gradient, matching `../00-architecture.md`'s own framing.

## Tests

- `SituationFilterView`: renders 8 group chips by default; clicking one reveals exactly that group's situation chips and collapses any previously-expanded group; a selected situation (from a deep link) auto-expands its group on mount.
- `LeafFacet`: renders nothing when `availableLeafCodes` is empty; renders a chip per code when not.
- `TagBadge`: opacity scales with the `confidence` prop; snapshot at `confidence=1.0` matches today's fully-opaque rendering (no visual regression for fully-confident tags).
- `DocumentRepository.list_page()`: fixture test confirming slug order when no situation filter is active, confidence order when one is, same shape as existing repository tests.
- `DocumentService.available_leaf_codes()`: empty for zero or 2+ selected situations; the right distinct set for exactly one.

## Verification

```bash
cd apps/api && ./ci.sh
cd apps/web && ./ci.sh
```

## Refactor gate

Confirm `apps/web/src/architecture.test.ts` still passes — the new `SituationFilterView/` folder follows the existing `<X>View/` + barrel convention, and nothing inside it imports a feature `services/*` module directly (components only, per `apps/web/CLAUDE.md`).

## Commits

- `feat(api): expose available leaf-refinement codes and order results by confidence within a selected situation`
- `feat(web): group-first situation filtering with a non-empty-only leaf refinement facet`
- `feat(web): render tag confidence as a visual gradient instead of a flat badge`

## Out of scope

Any change to what counts as a filter match (selecting a situation still filters exactly as today; groups and leaf refinement are navigation and sorting aids, not new filter semantics); the domain filter's `FilterGroup` (domains have no groups — unchanged); any new scoring or taxonomy logic (chapters 1–3, already shipped by the time this chapter starts).
