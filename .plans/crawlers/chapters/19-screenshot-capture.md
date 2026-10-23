---
name: "Chapter 19 — Screenshot capture"
overview: "A capture_screenshot task kind run by a Playwright worker in its own workflow, enqueued only for pages that yielded documents, skipping login walls."
todos:
  - id: enqueue
    content: "Extraction enqueues capture_screenshot once per page with mentions"
    status: pending
  - id: capture
    content: "Playwright handler behind an optional extra with a driver protocol"
    status: pending
  - id: guards
    content: "robots, private-address and login-wall guards; size fallback"
    status: pending
  - id: workflow
    content: "discovery-capture.yml and a marked integration job in ingest CI"
    status: pending
isProject: false
---

# Chapter 19 — Screenshot capture

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/crawlers-screenshot-capture` · **Status:** planned

**Depends on:** [14](14-artifact-model-and-api.md), [17](17-extractor-framework.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Capture visual evidence for pages that produced documents, as a separate, optional runtime. Screenshots are evidence (durable), unlike snapshots (working input). Per decision D13 a page that yielded nothing, or a login wall, gets no screenshot.

## Contract

**Enqueue.** The `extract_page` handler (chapter 17), after posting at least one mention, enqueues `capture_screenshot` through `POST /machine/tasks` with `target_url = final_url`, `input_key = "shot@1"`, priority 300. Identity dedupes it, so one page produces one capture however many extractor versions run. No mentions, no task.

**Package.** `pyproject.toml` gains the optional extra `capture` (`playwright`). The handler lives in `discovery_ingest/capture/` and talks to a small `PageDriver` protocol (`goto`, `screenshot`, `final_url`, `has_password_field`); the Playwright implementation is the only module importing `playwright`. The handler registry registers `capture_screenshot` only when the import succeeds, so the ingest CI job without browsers still passes. Starting `worker drain --kinds capture_screenshot` without the extra fails with a clear message **before** claiming anything.

**Capture behaviour.**

- Chromium, headless, viewport 1280×800, navigation timeout 30 s, `wait_until="networkidle"`, full-page screenshot clamped to 12,000 px height.
- robots.txt is honoured with the chapter 2 cache; denied is a permanent failure.
- Every request the page makes is routed through the chapter 2 address guard; requests to private, loopback or link-local addresses are aborted. Downloads are disabled.
- **Login wall** (final URL path or host contains `login`, `signin`, `auth` or `openid-connect`, or the page has a password input): complete the task with `result_note = "login_wall"` and upload nothing.
- PNG first; if it exceeds 8 MB re-encode as JPEG quality 80; if still too large fail permanently.
- Upload as a `screenshot` artifact with `fetched_at` set to the capture instant, `source_url` the task URL and `final_url` the page's final URL.
- Navigation timeout and 5xx are retryable; denials, login walls and oversize are not. A browser that cannot launch is an infrastructure error that fails the run, not the task.

**Workflows.**

- `.github/workflows/discovery-capture.yml`: `workflow_dispatch` with inputs for `max_batches` and `time_budget_seconds`, plus a daily schedule gated by the repository variable `DISCOVERY_CAPTURE_SCHEDULE=enabled`. Steps: checkout, Python, `pip install -e ".[capture]"`, `playwright install --with-deps chromium`, API health wait, `worker drain --kinds capture_screenshot`, report to the job summary. It shares the `discovery-drain` concurrency group.
- `discovery-ingest-ci.yml` gains a second job `capture-integration` that installs the extra and Chromium and runs tests marked `needs_playwright` against a local `http.server` fixture page. Unit tests never need a browser.

## TDD loops

### Loop A — Enqueue rule

**Red** (`test_extract_worker.py`)

1. `extract_page enqueues one capture task when mentions exist`.
2. `extract_page enqueues none when there are no mentions`.
3. `re-extraction with a new extractor version does not create a second capture task`.

**Green/Refactor:** one small helper called at the end of the handler.

### Loop B — Handler with a fake driver

**Red** (`test_capture_worker.py`)

1. `capture uploads a png screenshot artifact and completes`.
2. `capture completes with note login_wall and uploads nothing`.
3. `capture fails permanently when robots.txt disallows`.
4. `capture fails retryably on navigation timeout`.
5. `capture falls back to jpeg when the png is too large`.
6. `capture aborts requests to private addresses`.
7. `starting the capture kind without the extra fails before claiming`.

**Green:** handler built on `PageDriver`. **Refactor:** each guard is its own named function; the handler reads as a short pipeline.

### Loop C — Real browser (marked)

**Red** (`needs_playwright`): `capture produces a non-empty png of a local fixture page` and `capture detects a password field page as a login wall`. **Green/Refactor:** the Playwright driver only.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest -m "not needs_playwright" && ruff check . && mypy discovery_ingest
gh pr checks --watch                           # includes capture-integration
gh workflow run discovery-capture.yml -f max_batches=1
gh run watch && gh run view --log
```

Live gate (needs S1–S4 and at least one chapter 18 extraction): the run completes at least one capture; the screenshot is visible in the admin Artifacts panel; a known login URL yields `login_wall` without an upload. Record the run ID, artifact id and the storage bytes shown in Coverage.

## Out of scope

Capturing arbitrary catalogue pages, interaction scripts (clicks, form filling), cookie-banner dismissal, video, PDF capture, attaching screenshots to suggestions.
