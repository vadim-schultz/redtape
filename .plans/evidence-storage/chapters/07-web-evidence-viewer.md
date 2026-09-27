---
name: "Chapter 7 — Web evidence viewer"
overview: "The suggestion detail page shows each evidence item's fetched date with a screenshot thumbnail that opens full size, and a link to the raw HTML capture when present."
todos:
  - id: hook
    content: "useEvidenceQuery"
    status: pending
  - id: viewer
    content: "EvidenceSection, EvidenceThumbnail, EvidenceLightbox"
    status: pending
isProject: false
---

# Chapter 7 — Web evidence viewer

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/evidence-web-viewer` · **Status:** planned

**Depends on:** [6](06-evidence-read-endpoint.md), suggestion-interface [10](../../suggestion-interface/chapters/10-web-suggestion-list-and-detail.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Whoever reviews a suggestion (a moderator voting, or anyone curious) can see when it was fetched and what
the page looked like, without leaving `/suggestions/:id`.

## Design decisions

**Slice `apps/web/src/features/evidence/`**, hooks and components layout matching documents:

```
hooks/useEvidenceQuery.ts
containers/ (none — embedded, not its own page)
components/EvidenceSection.tsx     (renders under SuggestionDetailView, chapter shows fetched date list)
components/EvidenceThumbnail.tsx   (screenshot kind: <img>, click opens EvidenceLightbox)
components/EvidenceLightbox.tsx    (Chakra Dialog, full-size image)
components/EvidenceHtmlLink.tsx    (html kind: "View captured page" opening the presigned URL in a new tab)
components/EvidenceEmptyState.tsx
```

**One request, short-lived URLs.** `useEvidenceQuery` refetches on window focus disabled (the presigned URLs
are valid for 5 minutes, D6; a stale thumbnail simply re-fetches on next visit, not important enough for
aggressive invalidation) but does add a manual "Refresh" action if a URL 403s (`onError` on the `<img>` falls
back to a "reload evidence" prompt, tested).

**Fetched date formatting** reuses the existing locale-aware date formatting used elsewhere for
`created_at` (grep for the current helper; if none exists, add one small `formatDate(iso, locale)` in
`src/utils/`, shared rather than duplicated per feature — rule of three not yet met with one caller, so kept
minimal).

**Embedded, not a route.** `SuggestionDetailView` (suggestion-interface chapter 10) gains one composition
point (`<EvidenceSection suggestionId={id} />`); no new route.

**i18n**: `evidence.*` keys (`fetched_on`, `view_captured_page`, `no_evidence`, `image_unavailable`).

## Files

**Add** — `apps/web/src/features/evidence/{hooks/useEvidenceQuery.ts, services/evidenceApi.ts,
components/*}`, tests beside each.

**Edit** — `apps/web/src/features/suggestions/components/suggestion-detail/SuggestionDetailView.tsx`,
`apps/web/src/i18n/fallback/{de,en}.json`, `apps/api/scripts/seed_data/translations/{de,en}.json`.

## Red tests

| Test | Asserts |
| --- | --- |
| `useEvidenceQuery · fetches evidence for the suggestion id` | Query key and path |
| `EvidenceSection · shows a thumbnail per screenshot with its fetched date` | Render count and text |
| `EvidenceSection · shows a link for an html capture` | Anchor `href` and `target=_blank` |
| `EvidenceSection · shows the empty state when there is none` | Negative |
| `EvidenceThumbnail · clicking opens the lightbox with the full image` | Dialog visible |
| `EvidenceThumbnail · a broken image shows the unavailable state, not a blank box` | `onError` handling |
| `EvidenceLightbox · Escape closes it` | Keyboard |
| `i18n · every evidence.* key exists in both fallback bundles` | Parity |

## Green

1. Hook and API service; test 1.
2. Section rendering both kinds and the empty state; tests 2–4.
3. Thumbnail, lightbox, broken-image handling; tests 5–7.
4. i18n; test 8.

## Refactor gate

Each component stays one concern, ≤ ~60 LOC. Report the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/evidence src/features/suggestions
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual: open a suggestion with a screenshot and one with raw HTML; confirm the lightbox and the new-tab
link; wait past 5 minutes and confirm the broken-image fallback appears, then refresh.

## Out of scope

Uploading evidence from the web (crawler and API-driven only in this program), comparing evidence across
suggestion revisions.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/evidence-web-viewer
```

```text
test(web): describe the evidence viewer on the suggestion detail page

feat(web): add screenshot and HTML evidence viewer
```
