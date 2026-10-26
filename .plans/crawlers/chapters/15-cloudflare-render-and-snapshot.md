---
name: "Chapter 15 — Cloudflare render and snapshot"
overview: "Render pages through Cloudflare Browser Run quick actions on the free plan: a probe, a throttled client with a daily browser budget, a render_page task enqueued by fetch_url, rendered-HTML snapshots, and a workflow that drains the browser kinds."
todos:
  - id: probe
    content: "Browser probe CLI and manual workflow that settle the unknowns before the client depends on them"
    status: pending
  - id: client
    content: "BrowserClient port, Cloudflare adapter, throttle and run budget"
    status: pending
  - id: handler
    content: "render_page handler uploads the rendered DOM as a snapshot; release instead of fail on quota or storage problems"
    status: pending
  - id: enqueue
    content: "fetch_url enqueues render_page after a successful HTML fetch"
    status: pending
  - id: workflow
    content: "discovery-render.yml drains the browser kinds with both budgets, schedule gated by a variable"
    status: pending
isProject: false
---

# Chapter 15 — Cloudflare render and snapshot

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/crawlers-cloudflare-render` · **Status:** planned

**Depends on:** [02](02-fetcher-hardening.md), [14](14-artifact-model-and-api.md), [23](23-free-tier-guards.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

The plain fetch ([`_handle_fetch_url`](../../../apps/discovery-ingest/discovery_ingest/worker/drain.py)) downloads the body and discards it, and it never runs JavaScript. Many of the 123 hosts serve single-page shells or login redirects. This chapter stores the **rendered** page, so chapters 17 and 18 extract from what a citizen actually sees. Rendering is done by [Cloudflare Browser Run quick actions](https://developers.cloudflare.com/browser-run/examples/) (decisions D14, D19–D22); there is no browser in this repository, in any image or in CI.

The account already exists (the frontend runs on Cloudflare) and the **free plan** is used on purpose. Its limits shape the design:

| Free-plan limit | Consequence |
| --- | --- |
| 10 browser minutes per day | A run has a browser-time budget; the worker sums `X-Browser-Ms-Used` |
| 1 quick-action request every 10 seconds | One call at a time, at least 11 seconds apart (about 5 pages a minute) |
| 3 concurrent browsers, 60 s browser timeout | Single-threaded worker; navigation timeout 30 s |
| `429` with `Retry-After` when exceeded | Stop the run and **release** tasks; never fail them |

## Step 0 — Probe (blocking, manual)

Several response details are not in the public docs excerpts the plan was written from. `python -m discovery_ingest browser probe --url <u>` (repeatable) and the manual workflow `.github/workflows/discovery-browser-probe.yml` (`workflow_dispatch`, secrets `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_BROWSER_API_TOKEN`) call each endpoint the worker will use and print a table; secrets are never printed. It must report:

1. `/content` (and `/snapshot` with `formats: ["content", "markdown"]`) response shape: JSON envelope or raw body, and the `X-Browser-Ms-Used` header.
2. Whether the target's HTTP status or final URL is exposed anywhere. The design below does **not** depend on either (the plain fetch already provides both) and records the finding.
3. The result for a URL that returns 404 and for a host that does not resolve, so the error table in the client is filled from facts.
4. Whether `userAgent` and `rejectResourceTypes` (images, fonts, media) are honoured on `/content`, and the browser milliseconds a typical page costs with and without them.
5. `/screenshot` response (raw image bytes or JSON) against `/snapshot` with `formats: ["content", "screenshot"]` (JSON with a base64 image), the browser milliseconds each costs for the same page, and the byte size of a full-page JPEG quality 80 against PNG.
6. The rendered size of two or three real pages (a server-rendered one, and a single-page shell such as a `fimportal.de/detail/L/...` URL), compared with the plain-fetch body, to confirm the rendered DOM is richer and to check the 4 MB snapshot cap.
7. `Retry-After` and the body of a `429` if one occurs; the probe does not try to provoke one.

The probe is the first commit of this chapter. `workflow_dispatch` workflows only register once their file is on the default branch (the same limit that deferred the chapter 2 live gate), so run the probe from a local shell with the two variables exported (`python -m discovery_ingest browser probe ...`); the workflow serves later re-checks. The probe output and run ID or date go into the ledger. Anything that contradicts the contract below changes the contract before the client is written.

## Contract

**Settings** (`IngestSettings`, all optional): `cloudflare_account_id` (`CLOUDFLARE_ACCOUNT_ID`), `cloudflare_browser_api_token` (`CLOUDFLARE_BROWSER_API_TOKEN`, a custom token with only the "Browser Run - Edit" permission), `browser_min_interval_seconds` (default 11), `browser_request_timeout_seconds` (default 60). Nothing is required unless a browser kind is drained.

**Port** (`discovery_ingest/browser/`):

```text
class BrowserClient(Protocol):
    def render(self, url: str) -> RenderedPage: ...        # html: str, ms_used: int | None
    def screenshot(self, url: str) -> ScreenshotImage: ... # data, content_type, ms_used, html: str | None
```

`CloudflareBrowserClient` is the only module that knows endpoint paths, the bearer token, or the JSON envelope. Behaviour:

- `render` calls `/content` with `gotoOptions {waitUntil: "networkidle2", timeout: 30000}`, `userAgent` set to the identifying string from [config.py](../../../apps/discovery-ingest/discovery_ingest/config.py) (invariant 8), and `rejectResourceTypes` for images, fonts and media when the probe confirms it saves browser time.
- `screenshot` (used by chapter 19) calls `/snapshot` with `formats: ["content", "screenshot"]`, viewport 1280×800, `fullPage: true`, JPEG quality 80: one browser session yields the image **and** the DOM, so the login-wall guard can look at the page that was actually captured (`html` is set). If the probe shows `/snapshot` costs clearly more browser time than `/screenshot`, call `/screenshot` instead and leave `html` as `None` (the guard then uses the URL rule only). One call only; the free budget does not allow a PNG-then-JPEG retry. Over 8 MB is reported by the caller as oversize.
- An injected `Throttle` (clock and sleep are parameters, so tests never wait) enforces the minimum interval between **any** two Cloudflare calls in the process.
- `ms_used` comes from `X-Browser-Ms-Used`; when the header is absent the client measures the call duration instead, so the budget is never silently unbounded.
- **Error classification** (table finalised from probe item 3, defaults below):

  | Response | Meaning |
  | --- | --- |
  | `429` | `BrowserQuotaExceeded(retry_after)` |
  | `401`, `403` | `BrowserAuthError`: infrastructure; the run fails, tasks are released |
  | other `4xx` | permanent task failure (bad request) |
  | `5xx`, timeout, connection error | retryable task failure |

**Run budget.** `BrowserBudget(browser_seconds)` accumulates `ms_used`. `DrainPolicy` gains `browser_budget_seconds: float | None` (default `None`, which is only valid when no browser kind is drained; the CLI flag is `--browser-budget-seconds`, default 480 so a manual probe or a second run the same day still fits in the 600-second allowance). `StopReason` gains `browser_budget`, `browser_quota` and `storage_unavailable`; `DrainReport` gains `browser_seconds_used` and `released`.

**Shared daily ledger (chapter 23, decision D23).** The run budget alone cannot stop a second run, a local run or a probe from overspending the same UTC day. At start the worker reads `GET /machine/budgets` and uses `min(browser_budget_seconds, remaining browser seconds today)` (the ledger cap defaults to 480); a day already marked exhausted stops the run before claiming anything (`browser_budget`). Before every call it **reserves** an estimate (the 30 s navigation timeout, `POST /machine/budgets/browser_seconds/reserve`; a denial stops the run with `browser_budget`) and after the call it **adjusts** by `ms_used - estimate` (`/adjust`), so two concurrent runs cannot both take the last seconds. A `429` also calls `/exhaust`, so later runs that day stop at once. The ledger is a guard, not a dependency of correctness: if the budgets route is unreachable the worker falls back to its own run budget and reports `ledger_unavailable` in the drain report.

**`render_page` kind** (label added in chapter 14). Input: `target_url` is the final URL of the plain fetch. Handler order:

1. robots.txt for the URL, using the chapter 2 cache; denied is a permanent failure.
2. `client.render(url)`. `BrowserQuotaExceeded` releases this task (see below) and stops the run with `browser_quota`; an exhausted budget before the call stops with `browser_budget`.
3. **Login wall:** the rendered HTML has an `input[type=password]`, or the URL host or path contains `login`, `signin`, `auth` or `openid-connect`: complete with `result_note = "login_wall"` and upload nothing.
4. Over the 4 MB cap: complete with `result_note = "oversize"`, upload nothing.
5. Upload the UTF-8 bytes as an `html_snapshot` (`POST /machine/tasks/{id}/artifacts`) with `source_url = task.target_url`, `final_url = task.target_url`, `fetched_at` captured immediately after the render returns.
6. Call `after_snapshot(task, artifact)`; chapter 17 plugs the extractor enqueue into it and here it does nothing. The hook keeps this handler free of extractor knowledge.
7. Complete.

An upload `503` (storage unset) or `507` (the R2 byte cap of chapter 14 is reached) releases the task and stops the run with `storage_unavailable`. A `413` or `415` is a programming error: fail permanently.

**Release, not fail.** Quota and storage problems say nothing about the page. `DiscoveryMachineClient.release_task(task_id, reason, not_before=None)` calls `POST /machine/tasks/{id}/release` (chapter 14), which re-pends the task without consuming an attempt. On `browser_budget`, `browser_quota` or `storage_unavailable`, the drain releases the in-flight task **and every task claimed but not yet started in the batch**, then stops. Browser drains therefore claim small batches (workflow default `max_tasks=5`), so at most four tasks are released per stop.

**`fetch_url` enqueues the render.** After the fetch log row is appended and a fetch ends with status 200 and `text/html`, `_handle_fetch_url` enqueues `render_page` through `POST /machine/tasks` with `target_url = outcome.final_url`, the default `priority = 100` (the queue claims lower numbers first, so renders come before the priority-300 screenshots of chapter 19 in the browser drain), and no `input_key`. Identity dedupes it, so re-fetching a page does not create a second open render. Not enqueued when the final URL looks like a login wall (same rule as step 3), when the fetch failed, or for non-HTML. The task outcome of `fetch_url` never depends on the enqueue: an enqueue error is logged and counted (`render_enqueue_failed`), the fetch still completes. The plain fetch therefore remains the cheap gate: robots, pacing, redirects and status handling already happened, and no browser time is spent on 3xx, 4xx or login pages.

**Kind safety.** `render_page` and `capture_screenshot` are **never** in the default kinds. `worker drain --kinds` containing either requires both Cloudflare settings and `GET /machine/artifacts/status` (chapter 14) reporting storage enabled; otherwise it exits non-zero with a clear message **before claiming anything**. This keeps the daily HTTP drain from sleeping 11 seconds per task.

**Workflow `.github/workflows/discovery-render.yml`.** `workflow_dispatch` with inputs `max_tasks` (default 5), `max_batches` (default 40), `time_budget_seconds` (default 900), `browser_budget_seconds` (default 480) and `kinds` (default `render_page,capture_screenshot`); a daily schedule (05:00 UTC) gated by the repository variable `DISCOVERY_RENDER_SCHEDULE == 'enabled'`, off by default. Secrets: `DISCOVERY_API_URL`, `DISCOVERY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_BROWSER_API_TOKEN`. Same shape as `discovery-drain.yml` (health wait, report to the job summary, fail the job when `succeeded` is false), with `timeout-minutes` set, a first step that runs `python -m discovery_ingest budget show --require-remaining actions_minutes=<timeout-minutes> --require-remaining browser_seconds=30` and skips the drain when it exits 3 (an allowance is gone), and a final `if: always()` step that reports the job's minutes to the ledger (chapter 23); it uses the **same `concurrency` group** `discovery-drain`, so the two never overlap. A run that stops on `browser_budget`, `browser_quota`, `time_budget` or `queue_empty` succeeds; only infrastructure errors fail the job.

**Cost.** The rate limit, not the 10 browser minutes, is normally the binding constraint: a 900-second run renders about 80 pages. The 1,423 known pages need roughly 18 such runs, about 4.5 hours of runner time in total (one-off). This repository's GitHub Actions share is capped at **1,000 minutes a month**, of which a CI reserve (default 600) is not ours to spend, so the backlog should mostly run **locally** and the workflow serves as the occasional manual or scheduled top-up (chapter 23 skips it when the allowance is gone). The same command run locally costs no Actions minutes:

```bash
python -m discovery_ingest worker drain --kinds render_page --max-tasks 5 --max-batches 40 \
  --time-budget-seconds 900 --browser-budget-seconds 480
```

## TDD loops

All browser tests use a fake `BrowserClient` and an injected clock; no test touches the network or sleeps.

### Loop A — Client, throttle and budget

**Red** (`apps/discovery-ingest/tests/test_browser_client.py`, `test_browser_budget.py`; the adapter uses `httpx.MockTransport`)

1. `render posts the url with the identifying user agent and returns html and ms_used`.
2. `render falls back to the measured duration when X-Browser-Ms-Used is absent`.
3. `two calls are at least the minimum interval apart` — fake clock records the sleep.
4. `429 raises BrowserQuotaExceeded with Retry-After`; `401` raises `BrowserAuthError`; `5xx` and timeout are retryable; other `4xx` is permanent.
5. `budget reports exhausted once the summed ms_used passes the limit`.
6. `screenshot returns bytes and content type; an over-limit image is rejected`.

**Green:** one module per concern (client, throttle, budget, errors). **Refactor:** the adapter stays about a hundred lines; endpoint paths in one table.

### Loop B — `render_page` handler

**Red** (`test_render_worker.py`)

1. `render_page uploads the rendered html as a snapshot and completes`.
2. `render_page completes with note login_wall and uploads nothing` — password input, and a login URL.
3. `render_page completes with note oversize and uploads nothing`.
4. `render_page fails permanently when robots.txt disallows`.
5. `render_page releases the task and stops the run on quota exceeded` — including the unstarted tasks of the batch; no attempt consumed.
6. `render_page stops with browser_budget before calling the browser once the budget is spent`.
7. `render_page releases and stops with storage_unavailable on an upload 503`.
8. `render_page fails retryably on a 5xx from the browser and permanently on a 4xx`.
9. `after_snapshot receives the created artifact exactly once and is not called when nothing was stored`.
10. `render_page uses the smaller of the run budget and the ledger's remaining seconds, reserves an estimate before each call and adjusts to ms_used after it, and stops before claiming when the day is exhausted` — fake ledger client.
11. `a 429 marks the day exhausted in the ledger; an unreachable ledger falls back to the run budget and reports ledger_unavailable` (negative pair).
12. `an upload 507 releases the task and stops with storage_unavailable`.

**Green:** a pipeline of named steps (robots, render, classify, upload, hook, complete). **Refactor:** about five lines per step; the stop signal is one small exception handled in `_run_batch`.

### Loop C — Enqueue and kind safety

**Red** (`test_worker_drain.py`, `test_cli_worker.py`)

1. `fetch_url enqueues render_page with the final url after a 200 html response`.
2. `fetch_url does not enqueue for a failed fetch, a non-html body, a redirect-only result, or a login-wall url`.
3. `an enqueue error is counted and does not fail the fetch`.
4. `default kinds exclude render_page and capture_screenshot`.
5. `draining a browser kind without Cloudflare settings or without storage fails before claiming`.
6. `the drain report includes browser_seconds_used, released and the new stop reasons`.

**Green/Refactor:** the enqueue is a named step after the log append; `_handle_fetch_url` stays about five lines.

### Loop D — Probe and workflow (the probe is built **first**, Step 0)

**Red** (`test_browser_probe.py`) `probe prints a table and never prints the token`; `probe exits non-zero when settings are missing`. The workflow file is checked by the existing workflow lint in CI.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_browser_client.py tests/test_browser_budget.py tests/test_render_worker.py tests/test_worker_drain.py tests/test_browser_probe.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate (needs S1–S4 and S15–S17; S14 for old fetches):

```bash
gh workflow run discovery-browser-probe.yml -f urls="https://example.com,https://fimportal.de"   # Step 0, before writing the client
gh workflow run discovery-drain.yml -f kinds=fetch_url -f max_tasks=10 -f max_batches=1          # enqueues render_page
gh workflow run discovery-render.yml -f max_tasks=5 -f max_batches=2 -f time_budget_seconds=300
gh run view --log                      # report: completed N, released 0, browser_seconds_used, stop_reason
```

Then open the pipeline detail of one rendered row (the chapter 16 panel) or call `GET /api/v1/discovery/admin/catalogue/<id>/artifacts`, and confirm an `html_snapshot` that contains content the plain fetch did not (a single-page shell). Record the probe run ID, the render run ID, the artifact id, the observed browser seconds per page and the pages per run.

## Out of scope

Extraction (chapters 17 and 18), screenshots (chapter 19), a paid-plan fast path, the plain-first optimisation (storing the plain body for pages that are already server-rendered; see the open seams), browser sessions, Puppeteer or Playwright over CDP, cookie-banner handling, authenticated pages, backfilling snapshots other than by the operator re-pend (S14).
