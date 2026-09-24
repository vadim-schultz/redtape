---
name: "Chapter 5 — Page titles"
overview: "Documents list and detail headers use pageTitle Iceberg textStyle and text.secondary descriptions."
todos:
  - id: list-header
    content: "DocumentsListHeader pageTitle"
    status: pending
  - id: detail-header
    content: "DocumentHeader pageTitle + secondary description"
    status: pending
  - id: tests
    content: "Header component tests"
    status: pending
isProject: false
---

# Chapter 5 — Page titles

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-page-titles` · **Status:** planned

**Depends on:** [2](02-theme-system.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

List and detail primary titles use `Heading` with `textStyle="pageTitle"` (Iceberg). Descriptions use
`Text` with `color="text.secondary"`. No bare `size="lg"` headings remain on these surfaces.

## Design decisions

**Keep presentational components dumb.** Headers receive `title` / `description` props; containers
unchanged.

**No bold on Heading.** Rely on `pageTitle` text style only.

## Files

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/features/documents/components/documents-list/DocumentsListHeader.tsx` | `textStyle="pageTitle"`, `color="text.primary"` |
| `apps/web/src/features/documents/components/document-detail/DocumentHeader.tsx` | Same; fix invalid `color="muted"` on description |

**Add**

| Path | Contents |
| --- | --- |
| `DocumentsListHeader.test.tsx` | Colocated beside component |
| `DocumentHeader.test.tsx` | Colocated beside component |

## Red tests

| Test | Asserts |
| --- | --- |
| `DocumentsListHeader · renders title with pageTitle` | Title text visible; style prop or role heading |
| `DocumentHeader · renders title and description` | Both nodes when description provided |
| `DocumentHeader · omits description node when absent` | No description `Text` in DOM when prop null/undefined |

## Green

Update both headers; add tests with `renderWithProviders`.

## Refactor gate

Both components are tiny — expect ✅ no refactor needed unless merged into one component (do not merge; different call sites).

## Verification

```bash
cd apps/web
npm run test -- src/features/documents/components/documents-list/DocumentsListHeader.test.tsx src/features/documents/components/document-detail/DocumentHeader.test.tsx
cd ../.. && ./ci.sh
```

## Out of scope

DocumentCard (chapter 6). Section headers inside detail query status (chapter 9).

## Git workflow

```bash
git checkout -b feat/web-visual-page-titles
```

```text
feat(web): apply pageTitle textStyle to document list and detail headers
```
