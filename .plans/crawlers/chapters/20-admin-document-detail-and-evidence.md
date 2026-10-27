---
name: "Chapter 20 — Admin document detail and evidence"
overview: "A read-only candidate detail screen showing mentions with excerpts and procedure links, the evidence behind them, and emit state."
todos:
  - id: api
    content: "Candidate artifacts endpoint and mention artifact summaries"
    status: pending
  - id: page
    content: "Document detail page, mentions table, emit preview, suggestion state"
    status: pending
  - id: evidence
    content: "Reuse ArtifactsPanel for the evidence behind the mentions"
    status: pending
isProject: false
---

# Chapter 20 — Admin document detail and evidence

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/crawlers-admin-document-detail` · **Status:** planned

**Depends on:** [11](11-candidate-emit.md), [16](16-admin-artifacts-panel.md), [18](18-first-page-extractor.md) (optional; the live data can equally come from the [extraction](../../extraction/00-architecture.md) suite's `llm_extract`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Give the reviewer everything needed to decide whether a candidate is a real document before emitting it: where it was found, the surrounding text, the page evidence, and what the suggestion would look like.

## Contract

**API.**

- `GET /api/v1/discovery/admin/candidates/{id}` (chapter 6) mentions gain a small `artifact` summary (`id`, `kind`, `fetched_at`) when `artifact_id` is set.
- `GET /api/v1/discovery/admin/candidates/{id}/artifacts` returns the artifacts referenced by the candidate's mentions plus the latest screenshot of each distinct procedure, with presigned URLs (five-minute expiry), deduplicated by artifact id. Storage unset returns metadata with `url: null`.
- The emit preview route from chapter 11 is reused unchanged.

**Web** (`apps/web/src/features/discovery-admin/`):

- route `documents/:id` in `routes.tsx`; `containers/DiscoveryDocumentPage.tsx` owns the queries; `components/DocumentDetail.tsx`, `DocumentMentionsTable.tsx`, `DocumentEmitPanel.tsx` are presentational;
- header: locale-resolved title, `key`, status chip, jurisdiction, official URL (rendered as an external link with `rel="noopener noreferrer"` only when present);
- mentions table: role chip, excerpt, source field, `extractor@version`, source host, and a link to `/admin/discovery/pipeline/<catalogue_service_id>` for the procedure;
- evidence: the `ArtifactsPanel` from chapter 16, fed by the candidate artifacts query; screenshots first, snapshots as downloads;
- emit panel: the read-only preview (suggestion body or skip reason such as a slug conflict) and, once emitted, the suggestion id with its `pending` status. The screen has **no emit button**; emit remains a machine/CLI operator action (decision D16);
- the Documents list rows from chapter 10 now link to this route;
- strings under `discovery_admin.document.*` in German and English.

## TDD loops

### Loop A — API

**Red** (`test_discovery_candidates_api.py`, `test_discovery_artifacts_api.py`)

1. `candidate detail includes an artifact summary on mentions that have one`.
2. `candidate artifacts returns referenced artifacts and latest procedure screenshots without duplicates`.
3. `candidate artifacts degrades to null urls when storage is unset`.
4. `candidate artifacts rejects non-admins and returns 404 for an unknown candidate`.

**Green:** one query joining mentions to artifacts. **Refactor:** share the artifact DTO and presign helper with chapter 14.

### Loop B — Web

**Red** (Vitest)

1. `document page shows the title, status, mentions, and procedure links`.
2. `document page shows evidence from the artifacts panel and the empty evidence state`.
3. `document page shows the emit preview skip reason and the suggestion state after emit`.
4. `document page has no emit control` — asserts the absence of any button that posts.
5. `document route is guarded and shows not-found for an unknown id`.
6. `external url renders only when present and with rel noopener noreferrer`.

**Green:** container → hooks → presentational components. **Refactor:** extract a role-chip component shared with the list; keep each file about a hundred lines.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_candidates_api.py tests/test_discovery_artifacts_api.py
cd apps/web && npm run test -- src/features/discovery-admin && npm run lint && npm run format:check && npm run typecheck && npm run build
gh pr checks --watch
```

Live gate: as an allowlisted admin open a candidate that came from an LLM extraction or a chapter 18 extraction; its mentions link to procedures, its screenshot (chapter 19) and snapshot appear, and the preview matches what the CLI dry-run prints. Check the layout at phone width. Record the candidate id.

## Out of scope

Editing, merging or deleting candidates, an in-browser emit action, voting controls (voting-moderation chapters 10–11).
