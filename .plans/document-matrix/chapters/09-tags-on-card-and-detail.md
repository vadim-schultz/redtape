---
name: "Chapter 9 — Tags on card and detail"
overview: "Show a document's domains and life situations as badges on the detail header, linking back to filtered lists; list cards get tags only if the list API provides them."
todos:
  - id: detail
    content: "DocumentTags component in DocumentHeader from detail domains/life_situations"
    status: pending
  - id: list
    content: "Decide and, if needed, add tags to DocumentSummary; badges on DocumentCard"
    status: pending
isProject: false
---

# Chapter 9 — Tags on card and detail

**Repo:** `redtape` (`apps/web`, optionally `apps/api`) · **Branch:** `feat/matrix-document-tags` · **Status:** planned

**Depends on:** [4](04-documents-filter.md), [6](06-web-taxonomy-client.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

On `/documents/:id` the header shows the document's domains and situations as small badges; each links
to `/documents?domain=…` / `?situation=…`, connecting detail back to browsing. A document with no tags
shows nothing extra.

## Design decisions

**Detail first.** Chapter 4 already returns `domains` and `life_situations` on detail, so
`DocumentTags` slots into [DocumentHeader](../../../apps/web/src/features/documents/components/document-detail/DocumentHeader.tsx)
without backend work.

**List cards are a measured decision.** Adding tags to every list item means an extra join or
`selectinload` per page. Step 1 of Green measures the list endpoint with tags eager-loaded on the seeded
data; if cheap, extend `DocumentSummary` with `domains`/`life_situations` (backend commit in this
chapter, additive, defaulting to empty) and show badges on
[DocumentCard](../../../apps/web/src/features/documents/components/documents-list/DocumentCard.tsx);
otherwise defer and record the seam in [gaps-and-decisions.md](../gaps-and-decisions.md). Cards already
link to detail, so the feature is complete without list badges.

**One reusable badge group.** `components/document-tags/{DocumentTags, TagBadge}.tsx` shared by header
and card; badge styling from theme tokens, text from resolved API names (no client-side translation of
domain data).

**Absent means absent.** No empty wrapper, no "no tags" text, mirroring the card rule "missing
description → no `Card.Description` node".

## Files

**Add** — `apps/web/src/features/documents/components/document-tags/{DocumentTags,TagBadge}.tsx` + tests.

**Edit** — `apps/web/src/features/documents/types/index.ts`, `DocumentHeader.tsx` (+ test), and only
if the measurement passes: `DocumentCard.tsx`, `apps/api/app/schema/document/read.py`,
`apps/api/app/features/documents/{repository,service}.py`.

## Red tests

| Test | Asserts |
| --- | --- |
| `DocumentTags · renders a badge per domain and situation` | Count and text |
| `DocumentTags · each badge links to the filtered list` | `href` with slug |
| `DocumentTags · renders nothing when both arrays are empty` | Negative, no wrapper node |
| `DocumentHeader · shows tags when the detail has them` | Integration |
| `DocumentHeader · unchanged when the API omits the fields` | Backward-compat negative |
| `DocumentCard · shows badges when summary has tags` | Only if list tags added |
| `DocumentCard · no tags → no badge container` | Negative |

## Green

1. `TagBadge`, `DocumentTags`; header integration.
2. Measurement; then either the list-tag backend + card change, or the seam note.

## Refactor gate

- `DocumentHeader` must not exceed ~100 LOC; tags are composed as a child, not inlined.
- `DocumentTags` takes two arrays and delegates row rendering; no branching on axis inside JSX
  (pass a `{axis, items}` list to a single mapper).

## Verification

```bash
cd apps/web
npm run test -- src/features/documents
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: open a seeded document detail; click a badge; confirm the filtered list.

## Out of scope

Editing tags, tag counts, hover previews.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-document-tags
```

```text
test(web): describe document tag badges

feat(web): show domain and life situation tags on document detail
```
