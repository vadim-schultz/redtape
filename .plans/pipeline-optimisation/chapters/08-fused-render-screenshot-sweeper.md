---
name: "Chapter 8 — Fused render, screenshot sweeper and pruning"
overview: "Store the HTML and the screenshot of a page from one browser call, make screenshot capture a sweeper rather than a hook, and keep the latest five captures of each page."
todos:
  - id: canary
    content: "Extend browser probe to compare /content with fused /snapshot on about 25 stable pages"
    status: pending
  - id: fused
    content: "Upload the HTML and the screenshot from one render task, with the HTML first"
    status: pending
  - id: sweeper
    content: "Capture the screenshots of rendered pages that lack one, bounded per run"
    status: pending
  - id: pruning
    content: "Keep the newest five screenshots per page and never delete the only one"
    status: pending
isProject: false
---

# Chapter 8 — Fused render, screenshot sweeper and pruning

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-fused-render` · **Status:** planned
**Depends on:** [2](02-observability-run-hygiene.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3, item 1) · **Decisions:** D11, D16

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

Each page costs two navigations today: `/content` for the HTML in the render stage, and `/snapshot` for the screenshot, which is gated on the LLM stage. Use one `/snapshot` call for both, so a rendered page is also a screenshotted page, and make the screenshot capture a sweeper so it does not depend on an LLM task completing. Keep the newest five captures per page so R2 does not grow without bound.

## Design

- **Fused call.** `BrowserClient.screenshot()` (`browser/client.py`) already returns the DOM and the JPEG from one `/snapshot` call. `RenderPageHandler` (`worker/render.py`) uses it when the flag `RENDER_FUSED_SCREENSHOT` is on. The render stays on `/content` when the flag is off.
- **Upload order.** The HTML is uploaded first, then the `after_snapshot` hook runs (it enqueues the LLM work, as today), then the screenshot is uploaded best effort. A failed or oversize screenshot does not fail the task: the task completes with `result_note = "oversize_screenshot"` or `"screenshot_failed"`. `ScreenshotOversize` (raised in `_screenshot_image`) is caught here, not earlier, so the HTML is kept.
- **Consent tiers.** The fused body sends the tier-1 CSS (`CONSENT_HIDE_CSS`) and omits the tier-2 accept script, because the script can click a link and navigate away from the page being stored. The screenshot payload in `browser/payloads.py` (`snapshot_body`) gains a `consent_click: bool` argument, default off for the fused render.
- **Sweeper.** `capture_screenshot` tasks are produced by a sweeper: each run enqueues up to `SCREENSHOT_SWEEP_LIMIT` (default 50) for rendered catalogue services with no screenshot artifact, through the same path as `capture requeue`. The post-extraction hook (`enqueue_screenshot_for_mentions`) becomes a no-op when a screenshot already exists.
- **Pruning.** After a screenshot is stored, the API keeps the newest `SCREENSHOT_KEEP_PER_PAGE` (default 5) captures for the catalogue service and deletes the rest from R2 and the table. The existing `delete_old_snapshots` is HTML-only, so the screenshot path gets its own rule, with a kind filter. It never deletes the last capture of a page.
- **Canary.** Extend `python -m discovery_ingest browser probe` (`cli/browser/commands.py`) with `--canary N`. For N stable pages it fetches `/content` and the fused `/snapshot`, and compares the cleaned-text hash (`snapshot_translation/hash.py:source_hash`), block counts and link counts. Pass at 90% or more identical hashes, and no page losing more than 5% of its text or any link.

## Files

**Edit**

- `apps/discovery-ingest/discovery_ingest/worker/render.py`
- `apps/discovery-ingest/discovery_ingest/worker/capture_enqueue.py`
- `apps/discovery-ingest/discovery_ingest/worker/llm_extract.py` (the screenshot hook, if it still calls the old path)
- `apps/discovery-ingest/discovery_ingest/browser/client.py`
- `apps/discovery-ingest/discovery_ingest/browser/payloads.py`
- `apps/discovery-ingest/discovery_ingest/cli/browser/commands.py`
- `apps/api/app/features/discovery/artifact_upload.py`
- `apps/api/app/features/discovery/` (the snapshot pruning routine, next to `delete_old_snapshots`)
- `apps/api/app/config.py` (`SCREENSHOT_KEEP_PER_PAGE`)

**Do not edit**

- The consent tier-2 script itself (`browser/consent.py`). Only the fused body stops sending it.

## Red tests

| Test | Asserts |
| --- | --- |
| `one render task uploads the HTML and the screenshot from one call` | Happy: one browser request, two artifacts. |
| `the HTML is uploaded before the after-snapshot hook runs` | Happy: order of calls. |
| `an oversize screenshot keeps the HTML and completes with a note` | Negative: `result_note = "oversize_screenshot"`, HTML stored. |
| `a failed screenshot upload does not fail the task` | Negative: the task completes; the failure is logged. |
| `the fused body sends no accept script` | Negative: `addScriptTag` is absent. |
| `the sweeper enqueues only rendered pages without a screenshot` | Happy and negative: a page that already has one is skipped. |
| `pruning keeps the newest five and never the only capture` | Happy: six captures leave five; one capture is kept. |
| `the canary passes at 90% identical and fails below it` | Happy and negative, with recorded fixtures. |

## Green

1. Write the canary comparison test against fixtures first, then the canary command.
2. Write the upload-order test, then change `RenderPageHandler`.
3. Add the sweeper, then the pruning rule with its own tests.
4. Turn the flag on only after the live canary is recorded (see below).

## Refactor gate

`RenderPageHandler` stays under about five lines per method, with the screenshot upload as its own method. The pruning rule is one repository method, not a branch in the upload path.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest -q tests/ -k "render or browser or capture" && cd ../..
cd apps/api && PYTHONPATH=. .venv/bin/python -m pytest -q tests/ -k "artifact or screenshot" && cd ../..
./ci.sh
```

Live gate: run `browser probe --canary 25` with the flag still off. Record the hash identity, the block and link counts, and the browser seconds per page in the run ledger. Only then set `RENDER_FUSED_SCREENSHOT=true` on the worker. Check the R2 class A count for the first day against the budget table.

## Commits

`test(ingest): define the fused render canary`, `feat(ingest): add a canary to the browser probe`, `test(ingest): define the fused render upload order`, `feat(ingest): store the HTML and screenshot from one render`, `feat(ingest): capture screenshots of rendered pages with a sweeper`, `feat(api): keep the newest five screenshots of a page`.

## Out of scope

Browser Sessions (chapter 10), the refresh epoch (chapter 11), and the screenshot history UI (chapter 9).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-fused-render
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
