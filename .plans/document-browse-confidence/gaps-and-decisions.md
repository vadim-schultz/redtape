---
name: Document browse by confidence — Gaps and decisions
overview: "Settled decisions, assumptions, open seams and risks for making the candidate pool the single searchable, sortable document list with confidence shown as a traffic-light circle."
isProject: false
---

# Document browse by confidence — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

Decided with vadim.schultz on 2026-11-02 while scoping this suite.

| # | Decision |
| --- | --- |
| D1 | **Candidates become the list.** `/documents` is served by `GET /api/v1/candidates`. `GET /api/v1/documents`, `GET /api/v1/matrix` and web `/documents/:id` stay but are dormant: they only see `document` rows, and none remain once D6 lands. Emit, vote and promote are untouched and documented as dormant, because confidence replaces the accept/reject gate they implemented. |
| D2 | **Confidence bands: `< 0.4` red, `0.4 … < 0.7` yellow, `>= 0.7` green.** Constants in one module so they are easy to retune. One circle per card: the max tag score among the tags in the current filter (selected domain and situation codes), or the max over all tags when no chip is selected. |
| D3 | **Suggestions: unlink the UI only.** Remove the menu link and the `/suggest` route, and delete the `/suggest` page, `SuggestView/`, `useCreateSuggestion` and their tests. Keep `/suggestions` and `/suggestions/:id` (the admin emit panel links `DocumentEmittedState.tsx:17`), `formatRelativeTime` (imported by candidates and discovery-admin), the whole API, models and voting. i18n: remove only `nav.suggest` in all four locale files; the `suggest.*` and `suggestions.*` namespaces stay (parity tests require them non-empty). There is no "suggestion dialog" in the code: the UI is the `/suggest` page. |
| D4 | **Search and sort.** `q` is a title search over all locales (the existing `title_matches`, no index). The UI exposes sort by confidence (default, desc), title and newest (`created_at`), each asc/desc, URL-backed, composing with the chips. |
| D5 | **Menu closes on select** for navigation links, sign-out and the language flag; the colour-mode switch stays open (frontend-ui-menu D4). Home is centred. |
| D6 | **Seeded documents are removed** ("we'll just have real data from the db"). Stop seeding the 4 MVP `document` rows and 3 `document_requirement` rows, and delete exactly those rows from existing databases with a data migration. The seeded jurisdictions DE/SN/DD stay (`ID_DE` is the documented discovery secret; `fix_saxony_jurisdiction_leak` and the OpenPLZ reuse logic depend on them), and so does the taxonomy (domains, situations, groups). |

## Assumptions recorded as decisions

Stated at plan approval; change them before chapter 3 starts if wrong.

| # | Assumption |
| --- | --- |
| D7 | The circle uses stock Chakra `red`, `yellow`, `green` palettes (`colorPalette`), not brand `primary`, so a low-confidence ring is distinguishable from the swiss-red selected chips. |
| D8 | The new `/documents` card is the existing documents card plus tags and the circle. The completeness chips, the "complete only" switch, the "staged, unreviewed" banner and the `leaf` facet are not carried over. The `leaf` facet never worked: the `leaf` URL param was never sent to the API, and `available_leaf_codes` exists only on the `document` list. The API keeps `filter[complete]`. The municipality `LocationPicker` leaves the page too: it only fed `municipality_code` on the `document` list, and candidates have no jurisdiction filter. |
| D9 | Multi-select chips map to CSV filters (`filter[domain]=a,b`): OR within an axis, AND across axes. Group chips are expanded to their situation codes in the web; the API has no `group` filter. |
| D10 | Cards link to `/candidates/:id` (the existing item page with the flow diagram). `/candidates` redirects to `/documents`. Unifying the detail URL is not in scope. |

## Open seams

| # | Seam | Placeholder | Forcing condition |
| --- | --- | --- | --- |
| S1 | Dormant `document` API, `/documents/:id` and `/matrix` return nothing once D6 lands | Left in place | A later suite that removes the `document` read path, or promotes candidates differently |
| S2 | Completeness flags (`has_domain`, `has_situation`) still use the accepted-code rule with the 0.05 floor, so a candidate whose only tag scores below it shows a tag but no `has_*` flag | Flags unchanged; the new card does not show them, the item page checklist does | Someone reading the checklist and the tags on the same item page and finding them inconsistent |
| S3 | The score model is computed live from mentions on every list request, unindexed | Measured in chapter 11 | p95 of `/api/v1/candidates` above the budget set in chapter 11; then materialise `candidate_tag_scores` |
| S4 | Multi-chip card confidence is `max` over the selected codes, not a combined score | Pragmatic first choice, same as situation-tag-hierarchy's open seam | Usage showing a confusing order |
| S5 | Emit, vote, promote, the admin Emit panel and the suggestion API now have no purpose in the browse flow | Dormant and documented in chapter 10 | A removal suite; it would drop user-submitted requirement edges (`new_requirement`) and about 25 test files |
| S6 | Seeded-document deletion is irreversible (`downgrade()` is a no-op) | User-approved (D6) | None |
| S7 | `seed_documents.py` is renamed to `seed_jurisdictions.py`, which ripples through tests and docs | Done in chapter 8 | None |

## Risks

| Risk | Mitigation |
| --- | --- |
| A SQL noisy-OR (`1 - exp(sum(ln(1 - c)))`) drifts from the Python scorer on edge scores such as `c = 1.0` | Clamp the term, and a parity test over the world fixtures compares both within a tolerance (chapter 1) |
| Presence-based filtering makes every chip match many weak candidates | Intended (D1); ordering by confidence puts strong ones first, and the circle shows the weak ones as red |
| The delegated menu `onClick` closes on clicks that are not navigation | It matches only `a[href]` and the sign-out button; tests cover the colour switch and plain text |
| The data migration deletes a promoted document by accident | It deletes only the four stable UUIDs; a negative test keeps a non-seed document and its tags |
| Production still runs `start.sh` with `seed_documents` for one boot after deploy | The migration runs before the seed step in `start.sh`; chapter 8 removes the seed call in the same change |
