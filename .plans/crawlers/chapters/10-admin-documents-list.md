---
name: "Chapter 10 — Admin Documents list"
overview: "A read-only admin screen listing document candidates with search and filters, reachable from a new icon in the single menu row."
todos:
  - id: api-filters
    content: "Add q, min_mentions, role and source filters and mention-count ordering to the candidate list"
    status: pending
  - id: web-route
    content: "Documents list page, hooks, types, API function, route"
    status: pending
  - id: menu
    content: "Add the Documents icon (FaFileAlt) to DISCOVERY_MENU_LINKS"
    status: pending
isProject: false
---

# Chapter 10 — Admin Documents list

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/crawlers-admin-documents-list` · **Status:** planned

**Depends on:** [06](06-candidate-staging-model-and-api.md), [07](07-pvog-payload-harvester.md), [09](09-menu-icon-row.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

The admin must be able to see the documents the pipeline has found. This chapter gives a reviewer a sortable, filterable list of candidates before any emit exists, so quality problems in the harvester show up early.

## Contract

**API.** `GET /api/v1/discovery/admin/candidates` (chapter 6) gains `q` (case-insensitive substring over the title in any locale), `min_mentions`, `role` (candidates with at least one mention of that role), `source` (candidates mentioned by procedures of that catalogue source) and `sort` (`mentions_desc` default, `title_asc`, `newest`). Paging uses the shared `PageParams`.

**Web** (`apps/web/src/features/discovery-admin/`):

- route `documents` under `/admin/discovery/*` in `routes.tsx`, wrapped by `RequireDiscoveryAdmin` like its siblings;
- `containers/DiscoveryDocumentsPage.tsx` (data hooks), `components/DiscoveryDocumentsTable.tsx` and `components/DiscoveryDocumentFilters.tsx` (presentational), `hooks/useDiscoveryCandidatesQuery.ts`, `hooks/useDiscoveryDocumentFilters.ts`, and `listDiscoveryCandidates` in `services/discoveryAdminApi.ts`;
- table columns: title (locale-resolved with the same fallback as `PipelineDetail`), jurisdiction, roles, mention count, status, first seen; each row links to `/admin/discovery/documents/:id` (the detail page arrives in chapter 20; until then the link is rendered but the route shows the standard not-found view);
- loading, empty, error and unavailable states follow the existing `DiscoveryCatalogueQueryStatus` pattern;
- the menu gains `{ Icon: FaFileAlt, label: { de: "Dokumente", en: "Documents" }, to: "/admin/discovery/documents" }` in `DISCOVERY_MENU_LINKS`, rendered in the single `HStack` row from chapter 9. No new row, no text link.

## TDD loops

### Loop A — API filters

**Red** (`test_discovery_candidates_api.py`)

1. `candidate list filters by q across locales`.
2. `candidate list filters by min_mentions role and source`.
3. `candidate list sorts by mention count then title`.
4. `candidate list rejects an unknown sort or role` — 422.

**Green:** compose filters in the repository query; keep the controller thin.

**Refactor:** one filter-object parameter rather than a growing argument list.

### Loop B — Web

**Red** (Vitest, beside `DiscoveryCataloguePage.test.tsx`)

1. `documents page lists candidates with mention counts`.
2. `documents page sends filters and sort as query parameters`.
3. `documents page shows the empty and error states`.
4. `documents route is guarded` — a non-admin sees the disabled view and no data request is made.
5. `menu config contains the documents link and the row stays a single container` — extends the chapter 9 test.

**Green:** container → hooks → presentational table.

**Refactor:** share the pagination control with the Catalogue and Tasks pages instead of copying it.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_candidates_api.py
cd apps/web && npm run test -- src/features/discovery-admin src/components/layout/menu && npm run lint && npm run format:check && npm run typecheck && npm run build
gh pr checks --watch
```

Live gate: after the chapter 7 drain, open `/admin/discovery/documents` as an allowlisted admin; candidates appear with counts. Check the menu at phone width for a single row of six icons. Record observations.

## Out of scope

Candidate detail (chapter 20), emit actions, editing or merging candidates, exporting.
