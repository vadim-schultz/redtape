---
name: "Chapter 9 — Screenshot history Tabs"
overview: "On the public candidate page, show up to five captures of the newest screenshot's history as Chakra tabs, newest first and active, older ones to the right."
todos:
  - id: api-list
    content: "List a candidate's screenshots newest first, and serve each one by its artifact id"
    status: pending
  - id: api-schema
    content: "Add screenshots[] to CandidateDetail and keep screenshot for the transition"
    status: pending
  - id: web-tabs
    content: "Render the captures as Chakra Tabs with lazy mounting"
    status: pending
isProject: false
---

# Chapter 9 — Screenshot history Tabs

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-screenshot-tabs` · **Status:** planned
**Depends on:** [8](08-fused-render-screenshot-sweeper.md) (the retention bound) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3, item 7) · **Decisions:** D10, D11, D13

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

When a page has been re-shot, the candidate page shows only the newest capture. Show the history: up to five captures as tabs, the newest on the left and active, the older ones to the right and inactive. The admin thumbnail row is unchanged (D10).

## Design

- **Repository.** `ScreenshotRepository` (`apps/api/app/features/candidates/repository/screenshots.py`) gains `list_screenshots(candidate_id, limit)`. It is the existing `newest_screenshot` query without the `limit 1`, ordered by `fetched_at desc, id desc`, capped at `SCREENSHOT_KEEP_PER_PAGE`.
- **Service and route.** `ScreenshotService.serve_by_id(candidate_id, artifact_id, if_none_match)` returns one capture if its artifact belongs to a procedure that mentions the candidate, and answers 404 otherwise. The route is `GET /api/v1/candidates/{candidate_id}/screenshots/{artifact_id}` in `controller.py`, with the same ETag and immutable cache headers as today. It never returns a presigned URL.
- **Schema.** `CandidateDetail` (`apps/api/app/schema/candidate/read.py`) gains `screenshots: list[CandidateScreenshot] = []`. `screenshot` stays (D13). `detail.py` builds both from the same rows, so the newest entry matches `screenshot`.
- **Web.** `CandidateScreenshot.tsx` keeps its one-capture view. With two or more captures it renders `CandidateScreenshotTabs.tsx`, a Chakra v3 `Tabs.Root` with the newest tab as the default value. Panels use `lazyMount` and `unmountOnExit`, so only the active image is requested.
- **Labels.** A tab's trigger shows the relative time (`formatRelativeTime`), and its `title` shows the absolute date (`formatDate`). The tab list scrolls sideways on narrow screens.
- **Strings.** One new key for the tab list's label. The caption reuses `candidates.screenshot_fetched`.

## Files

**Edit**

- `apps/api/app/features/candidates/repository/screenshots.py`
- `apps/api/app/features/candidates/screenshot_service.py`
- `apps/api/app/features/candidates/controller.py`
- `apps/api/app/features/candidates/detail.py`
- `apps/api/app/schema/candidate/read.py`
- `apps/api/tests/` (the OpenAPI snapshot)
- `apps/web/src/features/candidates/types/detail.ts`
- `apps/web/src/features/candidates/services/candidatesApi.ts`
- `apps/web/src/features/candidates/components/CandidateDetailView/CandidateScreenshot.tsx`
- the locale message files that already hold `candidates.screenshot_*` keys

**Create**

- `apps/web/src/features/candidates/components/CandidateDetailView/CandidateScreenshotTabs.tsx` (and its test beside it)

**Do not edit**

- The admin screenshot thumbnail (`ScreenshotThumbnail.tsx`).

## Red tests

| Test | Asserts |
| --- | --- |
| `captures are listed newest first and capped at the keep limit` | Happy and boundary: six captures return five, newest first. |
| `a capture of another candidate's procedure is a 404` | Negative: the artifact id is valid, but no mentioning procedure links it. |
| `the per-capture route answers 304 for the current ETag` | Happy: `If-None-Match` matches. |
| `the detail's screenshot is the first entry of screenshots` | Happy: the two fields agree. |
| `the newest tab is selected by default` | Happy: web, the first tab has `aria-selected`. |
| `only the active capture's image is in the DOM` | Happy: lazy mount; other panels have no `img`. |
| `one capture renders no tab list` | Negative: the one-capture view is unchanged. |
| `a failed image shows the missing text on its tab only` | Negative: an `onError` on one tab leaves the others. |
| `arrow keys move between tabs` | Happy: keyboard navigation. |

## Green

1. Write the repository and the 404 test first, then the list query and the route.
2. Add the schema field and the OpenAPI snapshot update in the same commit.
3. Write the web one-capture and tab tests, then the tabs component. Keep each file under about 100 lines.

## Refactor gate

`CandidateScreenshot.tsx` stays the one-capture path and delegates to `CandidateScreenshotTabs.tsx` for two or more, so neither file gets a branch per count. `detail.py` builds both fields with one helper.

## Verification

```bash
cd apps/api && PYTHONPATH=. .venv/bin/python -m pytest -q tests/ -k "candidate and screenshot" && cd ../..
cd apps/web && npm run test -- src/features/candidates/components/CandidateDetailView --run && npm run lint && npm run typecheck && cd ../..
./ci.sh
```

Live gate: after the deploy, open a candidate with two captures on the staging API and confirm two tabs, the newest active, and that the older image is requested only after its tab is chosen.

## Commits

`test(api): define the screenshot history list and its 404`, `feat(api): list and serve a candidate's screenshot history`, `test(web): define the screenshot tabs`, `feat(web): show a candidate's screenshot history as tabs`.

## Out of scope

Admin thumbnails, zoom or lightbox controls, and any change to capture (chapter 8).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-screenshot-tabs
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
