---
name: "Chapter 16 — Admin Artifacts panel"
overview: "Show snapshots and screenshots for a catalogue row in the admin pipeline detail, with safe download-only handling for HTML and thumbnails for screenshots."
todos:
  - id: data
    content: "Types, API function, query hook with presign-aware staleness"
    status: pending
  - id: panel
    content: "ArtifactsPanel component and its slot in the pipeline page"
    status: pending
  - id: coverage
    content: "Artifact counts and bytes chips in Coverage"
    status: pending
isProject: false
---

# Chapter 16 — Admin Artifacts panel

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/crawlers-admin-artifacts-panel` · **Status:** planned

**Depends on:** [14](14-artifact-model-and-api.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

The admin must be able to see the evidence the pipeline collected. The panel is reused by the document detail page in chapter 20.

## Contract

Under `apps/web/src/features/discovery-admin/`:

- `types/index.ts`: `DiscoveryArtifact` (`id`, `kind`, `content_type`, `byte_size`, `source_url`, `final_url`, `fetched_at`, `url`), the list response, and the coverage `artifacts` field.
- `services/discoveryAdminApi.ts`: `listCatalogueArtifacts` using `apiRequest` like its siblings.
- `hooks/useDiscoveryArtifactsQuery.ts`: React Query with `staleTime` shorter than the presign lifetime (four minutes) and a refetch on window focus, so a thumbnail never uses an expired URL.
- `components/ArtifactsPanel.tsx` (presentational): groups by kind. Screenshots render as a lazy `<img>` thumbnail with a translated alt text that includes the capture date, linking to the full image in a new tab (`rel="noopener noreferrer"`). HTML snapshots render as a row with size, fetch date, final host and a **Download** link; the panel never renders snapshot HTML inline (no `iframe`, no `dangerouslySetInnerHTML`).
- States: loading skeleton, empty ("no artifacts yet"), error, and "storage not configured" when the API returns `url: null` for every item.
- `PipelineDetail.tsx` receives the panel through a slot prop like `preview`; `DiscoveryPipelinePage.tsx` wires the query, so components stay presentational and the architecture test's layering holds.
- Coverage view: chips for artifact counts and total bytes per kind, with a warning style when bytes pass 80 percent of a configured display budget (constant 1 GB for the free plan, defined once).
- Strings in `apps/web/src/i18n/fallback/{de,en}.json` under `discovery_admin.artifacts.*`.

## TDD loops

**Red** (Vitest, beside `PipelineDetail` and `DiscoveryPipelinePage.test.tsx`)

1. `artifacts panel shows a screenshot thumbnail with alt text and a new-tab link`.
2. `artifacts panel shows a download link for an html snapshot and never renders it inline` — asserts no `iframe` and no injected HTML.
3. `artifacts panel shows the empty state and the error state`.
4. `artifacts panel shows the storage-not-configured message when urls are null`.
5. `artifacts query refetches after the stale window` — fake timers.
6. `coverage view shows artifact bytes and highlights the budget warning`.
7. `all strings resolve in German and English` — the existing i18n fallback test pattern.

**Green:** container → hook → panel; keep URLs as opaque strings.

**Refactor:** one formatting helper for bytes and dates shared with the Tasks table; no duplicated locale logic.

## Verification

```bash
cd apps/web && npm run test -- src/features/discovery-admin && npm run lint && npm run format:check && npm run typecheck && npm run build
gh pr checks --watch
```

Live gate: after the chapter 15 live drain, open the pipeline detail of a fetched row; the snapshot appears, downloads, and its presigned link works within five minutes and fails after expiry (expected). Record the row id.

## Out of scope

Screenshot capture (chapter 19), document detail page (chapter 20), deleting artifacts, zoom or annotation tools.
