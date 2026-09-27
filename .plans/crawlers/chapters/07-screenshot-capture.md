---
name: "Chapter 7 — Screenshot capture"
overview: "ScreenshotCapture uses Playwright to render a page and save a full-page PNG with the capture instant, isolated behind the needs_playwright marker so the rest of the suite's tests stay fast and browser-free."
todos:
  - id: capture
    content: "ScreenshotCapture.capture(url) -> CapturedScreenshot(bytes, fetched_at)"
    status: pending
  - id: marker
    content: "needs_playwright tests and CI browser install"
    status: pending
isProject: false
---

# Chapter 7 — Screenshot capture

**Repo:** `redtape` (`apps/crawler`) · **Branch:** `feat/crawler-screenshot` · **Status:** planned

**Depends on:** [1](01-crawler-package-skeleton.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`ScreenshotCapture.capture(url) -> CapturedScreenshot(png_bytes, fetched_at, content_type="image/png")`, the
piece that turns a candidate's source page into evidence bytes ready for
[evidence-storage](../../evidence-storage/00-architecture.md)'s upload contract.

## Design decisions

**Playwright, headless Chromium** (D8): `sync_playwright()` context, `page.goto(url, wait_until="load")`,
`page.screenshot(full_page=True, type="png")`. `fetched_at = datetime.now(timezone.utc)` captured
immediately before the screenshot call, matching the evidence model's meaning of the field
([evidence-storage architecture §4](../../evidence-storage/00-architecture.md)).

**Timeout and failure**: a page that does not load within a fixed timeout (30s) raises
`ScreenshotCaptureError(url, reason)` — caught by the orchestrator (chapter 9) as a per-candidate failure,
never crashing the whole run.

**Test isolation via `needs_playwright`** (chapter 1's marker): these tests spin up a real (if headless)
browser against a tiny local HTML fixture served by `pytest`'s built-in `tmp_path` plus Python's
`http.server` in a background thread — not the real internet, but a real browser, which is what makes them
slow and worth isolating. Every other chapter's tests run without a browser installed at all.

**CI**: the workflow (chapter 10) runs `playwright install --with-deps chromium` only in the job step that
runs `needs_playwright` tests; the fast lint/unit job (chapter 1's workflow) never installs it.

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/pyproject.toml` | `playwright` |
| `apps/crawler/crawler/screenshot.py` | `ScreenshotCapture`, `CapturedScreenshot`, `ScreenshotCaptureError` |
| `apps/crawler/tests/test_screenshot.py` | Tests below, all marked `needs_playwright` |
| `apps/crawler/tests/support/local_server.py` | Tiny HTTP server fixture for a local page |

## Red tests

| Test | Asserts |
| --- | --- |
| `ScreenshotCapture.capture · returns PNG bytes for a real page` | Starts with the PNG magic bytes |
| `ScreenshotCapture.capture · sets fetched_at close to the call time` | Within a few seconds |
| `ScreenshotCapture.capture · captures the full page, not just the viewport` | Fixture page taller than one viewport; image height reflects it |
| `ScreenshotCapture.capture · raises ScreenshotCaptureError for a page that never loads` | Fixture that hangs, or an unreachable port |
| `ScreenshotCapture.capture · raises for a non-existent local URL rather than hanging` | Bounded by timeout |

## Green

1. Local server fixture; happy path; tests 1–3.
2. Timeout and error handling; tests 4–5.

## Refactor gate

`capture` stays ≈5 LOC: open, screenshot, wrap the result. Report the outcome.

## Verification

```bash
cd apps/crawler
playwright install chromium
python -m pytest tests/test_screenshot.py -m needs_playwright
```

## Out of scope

Uploading the screenshot as evidence (chapter 8).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-screenshot
```

```text
test(crawler): describe screenshot capture, timing and failure handling

feat(crawler): add ScreenshotCapture with Playwright
```
