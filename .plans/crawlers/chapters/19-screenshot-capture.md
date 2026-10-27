---
name: "Chapter 19 — Screenshot capture"
overview: "A capture_screenshot task kind served by the Cloudflare client from chapter 15, enqueued only for pages that yielded documents, skipping login walls, and drained by the same throttled browser workflow."
todos:
  - id: enqueue
    content: "Extraction enqueues capture_screenshot once per page with mentions"
    status: pending
  - id: capture
    content: "capture_screenshot handler on the BrowserClient port with the shared quota and storage stop rules"
    status: pending
  - id: guards
    content: "robots, login-wall and oversize guards"
    status: pending
  - id: workflow
    content: "Live capture through discovery-render.yml; no new workflow, extra or CI job"
    status: pending
isProject: false
---

# Chapter 19 — Screenshot capture

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/crawlers-screenshot-capture` · **Status:** planned

**Depends on:** [14](14-artifact-model-and-api.md), [15](15-cloudflare-render-and-snapshot.md), [17](17-extractor-framework.md), [23](23-free-tier-guards.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Capture visual evidence for pages that produced documents. Screenshots are evidence (durable), unlike snapshots (working input). Per decision D13 a page that yielded nothing, or a login wall, gets no screenshot. The browser is Cloudflare's (decision D14): this chapter adds no Playwright, no optional extra, no new workflow and no CI job. It is a handler on the client, throttle and budget that chapter 15 built.

## Step 0 - Probe (run 2026-10-27, local shell, no secrets recorded)

Chapter 15 built `screenshot()` from the documented shapes only. Four calls through `browser probe` (one request per 11 s, the first process for `example.com`, a second for the SPA page) settled the open questions:

| # | Variant (endpoint) | Target | HTTP | `X-Browser-Ms-Used` | Response | Image bytes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `screenshot-jpeg` (`/screenshot`, full page, JPEG q80, 1280x800) | `https://example.com` | 200 | 1262 | raw `image/jpeg`, no envelope | 63,443 |
| 2 | `screenshot-png` (`/screenshot`, full page, PNG) | `https://example.com` | 200 | 4232 | raw `image/png`, no envelope | 75,533 |
| 3 | `snapshot-shot` (`/snapshot`, `formats: [content, screenshot]`, same options) | `https://example.com` | 200 | 1179 | JSON `{success, result{content str 2,373 B, screenshot base64}, meta{status 200, finalUrl, title, headers}}` | 63,443 (identical to row 1) |
| 4 | `screenshot-jpeg` | `https://fimportal.de/detail/L/99155004000000` | 200 | 2235 | raw `image/jpeg`, no envelope | 299,161 |

Browser time spent by this probe: 8,908 ms by the headers (the earlier chapter 15 probe used about 17 s, so about 26 s of the 600 s that day). No `429`, `401` or `403` occurred. Findings, and what each changed:

- **P1: `/screenshot` is raw bytes, `/snapshot` is JSON.** The client keeps `/snapshot` (JSON envelope, base64 image), as built. It costs no more browser time than `/screenshot` (1,179 against 1,262 ms, one sample each), and it returns the DOM, so the password-field guard works and is not URL-only.
- **P2: `/snapshot` also returns `meta.status` and `meta.finalUrl`** (the shape of F2 and F3). **Contract change:** `ScreenshotImage` carries `http_status` and `final_url`; the handler refuses an error status exactly as `render_page` does (5xx retryable, 4xx permanent, nothing uploaded), the login rule also looks at `meta.finalUrl`, and the artifact's `final_url` is `meta.finalUrl` (else `task.target_url`).
- **P3: JPEG against PNG.** JPEG q80 is smaller on the SPA-size page and 3.4 times faster on `example.com` (1.3 s against 4.2 s). JPEG stays. Both are far below the 8 MB cap; the full-page option was accepted (no error) and the 299 KB image for the fimportal page is consistent with a full page, but pixel dimensions were not measured.
- **P4: `X-Browser-Ms-Used` was a readable integer on all four calls.** The fraction and fallback handling of chapter 15 stays as a safety net.
- **P5: oversize costs browser time.** The client raises `ScreenshotOversize` after the call finished, so the exception now carries `ms_used` and the handler books it, otherwise an oversize page would be reserved but never settled.
- **Not probed:** the daily-limit `429` body and a login page. The `/snapshot` option `fullPage` against a page taller than 8 MB of JPEG is the open seam named below.

## Contract

**Enqueue.** Any extractor handler that posts at least one mention (the `extract_page` handler of chapter 17, and the `llm_extract` handler of the [extraction](../../extraction/00-architecture.md) suite) calls one shared helper, `enqueue_screenshot_for_mentions(...)`, which enqueues `capture_screenshot` through `POST /machine/tasks` with `target_url` = the extract task's own `target_url` (the artifact's `source_url`, which is the redirect-resolved URL of the plain fetch; `PageContext.final_url` is always `None` in the extract handler, chapter 17), `input_key = "shot@1"`, priority 300 (claimed after renders, because the queue takes lower numbers first). Identity dedupes it, so one page produces one capture however many extractor versions run. No mentions, no task. An enqueue error is logged and counted (`capture_enqueue_failed` in the drain report, beside `render_enqueue_failed`); it never fails the extraction.

**Handler** `handle_capture_screenshot`, registered in the task-kind table beside `render_page`. Steps, each a named function:

1. robots.txt for the URL (chapter 2 cache); denied is a permanent failure.
2. URL login-wall rule (the same function as chapter 15): complete with `result_note = "login_wall"`.
3. `client.screenshot(url)` (chapter 15 port). Quota exceeded, an exhausted run budget or daily ledger, or a storage `503` or `507` follow the chapter 15 rules exactly (the same ledger, the same `browser_seconds` resource): **release** this task and every unstarted task of the batch, then stop with `browser_quota`, `browser_budget` or `storage_unavailable`. Nothing is failed because of a limit.
4. **Page status (probe P2):** `meta.status` of 400 or higher fails the task (5xx retryable, 4xx permanent), nothing uploaded. **Login wall by content:** when the DOM came back (`html` set) and it has an `input[type=password]`, or `meta.finalUrl` looks like a login URL: complete with `result_note = "login_wall"`, upload nothing.
5. Over 8 MB: complete with `result_note = "oversize"`, upload nothing; the browser time of the call is booked (probe P5). A viewport-only retry is an open seam, not built.
6. Upload as a `screenshot` artifact (`image/jpeg`) with `source_url = task.target_url`, `final_url = meta.finalUrl` (else `task.target_url`), `fetched_at` captured when the call returned.
7. Complete.

Errors follow the chapter 15 table: `5xx`, timeout and connection errors are retryable; other `4xx` are permanent. A rejected token (`BrowserAuthError`) is infrastructure: release, stop the run, fail the job.

**Why a page can still be a login wall here.** Chapter 15 never snapshots login walls, so an extracted page was not one when rendered. Content can change or redirect later, which is why the guard runs again on the captured DOM. Evidence of a login page has no value.

**No new runtime.** Capture runs in `discovery-render.yml` (chapter 15, default kinds `render_page,capture_screenshot`), under the same two budgets (run wall clock and browser seconds) and the same `discovery-drain` concurrency group. `DISCOVERY_RENDER_SCHEDULE` gates the daily schedule. There is no `[capture]` extra, no `PageDriver`, no `discovery-capture.yml` and no `capture-integration` CI job.

**Volume.** Screenshots are taken only for pages with mentions, so the count is a fraction of the rendered pages and stays well under the R2 byte cap of chapter 14 (JPEG, typically a few hundred kilobytes); each also costs one browser call in the same 11-second cadence.

## TDD loops

All tests use the fake `BrowserClient` and injected clock from chapter 15.

### Loop A — Enqueue rule

**Red** (`test_extract_worker.py`)

1. `extract_page enqueues one capture task when mentions exist, through the shared helper that the llm_extract handler also uses`.
2. `extract_page enqueues none when there are no mentions`.
3. `re-extraction with a new extractor version does not create a second capture task`.
4. `a failed capture enqueue is counted and does not fail the extraction`.

**Green/Refactor:** one small helper called at the end of the handler.

### Loop B — Handler

**Red** (`test_capture_worker.py`)

1. `capture uploads a jpeg screenshot artifact and completes`.
2. `capture completes with note login_wall for a login url without calling the browser`.
3. `capture completes with note login_wall and uploads nothing when the captured dom has a password field`.
4. `capture completes with note oversize and uploads nothing for an image over 8 MB`.
5. `capture fails permanently when robots.txt disallows`.
6. `capture releases the task and stops the run on quota exceeded, budget spent, or storage unavailable` — unstarted tasks of the batch are released too and no attempt is consumed.
7. `capture fails retryably on a 5xx and permanently on a 4xx from the browser`.
8. `capture still works when the client returns no dom` — the URL rule is the only guard.

**Green:** handler built on the port. **Refactor:** each guard is its own named function shared with `render_page` where the rule is identical; the handler reads as a short pipeline.

### Loop C — Kind registry

**Red** (`test_worker_drain.py`) `capture_screenshot is dispatched to its handler, and is absent from the default kinds`. **Green/Refactor:** one table entry.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_extract_worker.py tests/test_capture_worker.py tests/test_worker_drain.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
gh workflow run discovery-render.yml -f kinds=capture_screenshot -f max_tasks=5 -f max_batches=1
gh run watch && gh run view --log
```

Live gate (needs S15–S17 and at least one chapter 18 extraction): the run completes at least one capture; the screenshot is visible in the admin Artifacts panel; a known login URL completes with `login_wall` and no upload. Record the run ID, artifact id, the browser seconds reported and the storage bytes shown in Coverage.

## Out of scope

Capturing arbitrary catalogue pages, interaction scripts (clicks, form filling), cookie-banner dismissal, video, PDF capture, a viewport-only retry for oversize pages, attaching screenshots to suggestions.
