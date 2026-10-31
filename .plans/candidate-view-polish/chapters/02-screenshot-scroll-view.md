---
name: "Chapter 2 — Scrollable screenshot"
overview: "Replace the evidence screenshot's cropped 16:10 box with a fixed max-height, vertically scrollable frame showing the full captured page at its natural aspect ratio."
todos:
  - id: frame
    content: "Swap aspectRatio+overflow:hidden+objectFit:cover for a max-height, overflowY:auto frame with the image at natural size"
    status: pending
isProject: false
---

# Chapter 2 — Scrollable screenshot

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/candidate-view-polish-scroll-view` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 4) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view-polish` · **Release branch:** `main`

## Goal

`CandidateScreenshot.tsx`'s `ScreenshotFrame` crops the full-page capture to a fixed 16:10 box (`aspectRatio={16/10}`, `overflow="hidden"`, `objectFit: "cover"`, `objectPosition: "top"`), so everything below the first viewport of a tall source page is invisible and inaccessible. Show the whole captured image inside a frame of reasonable fixed height, reachable by scrolling.

## Design decisions

- **Frame.** Replace `aspectRatio={16/10}` + `overflow="hidden"` with a fixed `maxH` (e.g. a value consistent with the detail page's other sections — pick one that shows a useful amount, such as `maxH="70vh"`, and justify the chosen value in the PR description) and `overflowY="auto"`, `overflowX="hidden"`. Keep the existing `borderWidth`/`borderColor`/`bg="surface.muted"` so the frame still reads as a distinct box.
- **Image.** Drop `objectFit: "cover"`/`objectPosition: "top"`; set `width: "100%"`, `height: "auto"` so the image renders at its natural aspect ratio, full width, and scrolls within the frame rather than being clipped.
- **Scrollbar visibility.** Use the browser's native scrollbar (no custom scrollbar styling) so the frame visibly signals there's more content below, consistent with how the rest of the app handles overflow (check `AppLayout`/other scroll containers for an existing convention before introducing a new one).
- **Nothing else changes.** `fetchedAt` text, the missing-screenshot fallback, `loading="lazy"`, `onError` handling, and the `alt` text all stay as they are — this chapter touches only the frame's sizing/overflow and the image's own sizing styles.

## Files

**Edit**

- `apps/web/src/features/candidates/components/CandidateDetailView/CandidateScreenshot.tsx`
- its test file (create if one doesn't already exist beside it; check first)

**Do not edit**

- `CandidateEvidence.tsx`, `CandidateSources.tsx`
- The capture pipeline (chapter 1) or the screenshot-serving API

## Red tests

| Test | Asserts |
| --- | --- |
| `the screenshot frame is vertically scrollable` | Happy: the frame container has `overflowY` set to a scrollable value (`auto`/`scroll`) and a bounded max height, not `overflow: hidden`. |
| `the image renders at its natural aspect ratio` | Happy: the `<img>` has no `objectFit: cover` and no fixed aspect-ratio box constraining it — width is 100%, height is auto. |
| `the missing-screenshot and error fallbacks are unchanged` | Negative: `src: null` and an `onError` trigger still render the existing fallback text, not the frame. |
| `fetchedAt still renders below the frame` | Happy: the relative-time caption still appears when `fetchedAt` is present. |

## Green

1. Replace the `Box` props on `ScreenshotFrame`: drop `aspectRatio`/`overflow="hidden"`, add `maxH`/`overflowY="auto"`/`overflowX="hidden"`.
2. Replace the `<img>` inline style: drop `objectFit`/`objectPosition`, set `height: "auto"`.
3. Re-run the existing fallback/error tests to confirm no regression, then add the new scroll/aspect-ratio assertions.

## Refactor gate

Audit `CandidateScreenshot.tsx`: confirm it's still under the file's size discipline (it's a small file; this change shouldn't grow it meaningfully), and that the frame's sizing values are a named constant if they're reused anywhere else (they likely aren't — one file is fine without extraction). Report the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/candidates/components/CandidateDetailView/CandidateScreenshot --run
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Commits

`test(web): define the scrollable screenshot frame`, `feat(web): show the full-page screenshot with a vertical scrollbar`.

## Out of scope

Zoom, lightbox, or pan controls; thumbnails; any change to how the screenshot is captured (chapter 1) or served.

## Git workflow

```bash
git checkout feat/plans-candidate-view-polish && git pull
git checkout -b feat/candidate-view-polish-scroll-view
```

Open the chapter PR into `feat/plans-candidate-view-polish`.
