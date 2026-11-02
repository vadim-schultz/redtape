---
name: "Chapter 10 — Docs sync"
overview: "Bring the operator and planning docs in line with the new flow: candidates are the document list, emit/vote/promote are dormant, the list is searchable and sortable, and the sample documents are gone."
todos:
  - id: candidate-view
    content: "candidate-view.md: it powers /documents; default sort, filters, no floor"
    status: pending
  - id: admin-tables
    content: "admin-tables.md: drop the 'first 20 only' statement"
    status: pending
  - id: dormant
    content: "discovery-layer.md and suggestion-api.md: emit, vote, promote documented as dormant; fix the stale voting sentence"
    status: pending
  - id: smoke
    content: "deployment-checklist.md smoke checks for the candidate-backed /documents"
    status: pending
  - id: index
    content: "STATUS.md and .plans/README.md"
    status: pending
isProject: false
---

# Chapter 10 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `feat/document-browse-confidence-docs-sync` · **Status:** planned
**Depends on:** Chapter 9 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

The docs describe what runs. Apply the technical-writing conventions of the repo's other docs (short, present tense, tables for contracts). Paths relative to the repo root.

## Changes

| File | Change |
| --- | --- |
| `docs/operations/candidate-view.md` | The candidate API now backs `/documents`. Document: `q`, `sort_by` (adds `confidence`), `sort_order`, CSV `filter[domain]` / `filter[situation]` (any score, OR within an axis, AND across axes, at most 20 codes), the default order (confidence desc, then completeness, mentions), `confidence` on tags and cards, the removed 0.05 floor on this path, `/candidates` redirecting to `/documents`, the item page staying at `/candidates/:id`. Update the smoke checks. |
| `docs/operations/admin-tables.md:37` | The decision D11 line "public `/documents` and `/suggestions` show at most the first 20 rows by design" is no longer true for `/documents` (paged, searchable, sortable). Keep the `/suggestions` part. |
| `docs/operations/deployment-checklist.md:32-33,177-178` | Replace "expected 4 documents seeded" smoke checks with candidate-backed checks (`GET /api/v1/candidates` returns a page, `/documents` renders cards with a confidence circle). Chapter 8 already removed the seeded-document wording; keep that consistent. |
| `docs/operations/discovery-layer.md` (≈4, 22-23, 133-165, 205-215, 249-251, 258-285, 312-314, 450-482) | State that emit → vote → promote is **dormant**: documents are no longer published through it, the browse flow reads candidates directly. Update the tag-confidence paragraph (the 0.05 floor now applies only to the emit payload). Keep the machine routes documented. |
| `docs/operations/suggestion-api.md` | Remove the stale sentence "nothing in this API approves, rejects, or promotes … (the not yet built `voting-moderation` suite)": voting exists. Add that the web UI no longer links to the submit form (`/suggest`), that the API is unchanged, and that the dormant status follows D3/S5. |
| `docs/planning/STATUS.md`, `docs/planning/02-incremental-mvp-roadmap.md` | One line each: the document list is candidate-backed. Keep relative links valid (`test_discovery_docs_sync.py` checks them). |
| `.plans/README.md` | Status of this suite: shipped. Keep the index entry added with the suite. |
| `.plans/frontend-ui-menu/00-architecture.md` | The menu no longer has the `/suggest` or `/candidates` links; Home is centred and the menu closes on select (one-line pointers to this suite). |

## Tests and verification

The docs-sync tests must stay green: `tests/test_discovery_docs_sync.py`, `tests/test_discovery_operations_runbook.py`, `tests/test_deployment_checklist.py`, `tests/test_crawlers_docs*.py`, `tests/test_extraction_docs*.py`.

```bash
cd apps/api && uv run pytest tests/test_discovery_docs_sync.py tests/test_deployment_checklist.py tests/test_discovery_operations_runbook.py
./ci.sh
```

Negative check: `rg "seed_documents|expected 4 documents|first 20 rows" docs apps/api/README.md` returns no stale hit except in historical `.plans/` files, which are not rewritten.

## Commits

- `docs: describe the candidate-backed document list and mark emit/vote/promote dormant`

## Out of scope

Rewriting historical plan suites; documenting the removal of the dormant stack (a future suite).
