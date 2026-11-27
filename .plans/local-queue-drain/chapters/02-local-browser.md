# C2 — Local browser

**Depends on:** C0 · **Batch:** 1 · **Branch:** `feat/local-queue-drain-browser`

## Goal

Render and screenshot `render_page` and `capture_screenshot` tasks in a local headless Chromium, behind the existing `BrowserClient` port, without spending Cloudflare Browser Run seconds.

## Measurement gate first (no code)

1. Confirm the local render path passes `screenshot_sweep_limit=None` (D10), so the run queues no `capture_screenshot` tasks of its own.
2. Install Playwright with `uv` into the scratchpad venv, then `playwright install chromium`. The CDN answered on probe, but the install is the real test. If it fails, stop: record the failure and the proxy or certificate reason.
3. Run the 50 canary pages (`browser/canary.py` holds the list) through a throwaway Playwright script in the scratchpad. Record, per page: HTTP status, final URL, HTML length, JPEG length and time. This is the local baseline.
4. Run the same 50 pages through `CloudflareBrowserClient` (the canary already does this) and compare the status, the final URL and the HTML length. Gate: the final URL and status agree on at least 45 of 50, and the screenshot is a readable JPEG on every page that Cloudflare returned one for.
5. Repeat step 3 with Patchright. Record the blocked count. The probe decides O5: switch to Patchright only if stock Playwright blocks materially more of the 50 pages than Patchright does.

## Slices (red → green → refactor each)

### Slice 2a — render

- **Happy:** `LocalPlaywrightBrowser.render(url)` against a local fixture server returns `RenderedPage` with the rendered DOM (the fixture's JavaScript-written element is present), `http_status` 200 and `final_url` equal to the fixture URL.
- **Negative:** a navigation timeout (a fixture that never answers, with a 1 s timeout in the test) raises `BrowserRequestError` with `retryable=True`, and `ms_used` is a positive number. It does not return an empty page.

### Slice 2b — screenshot and consent

- **Happy:** `screenshot(url)` returns `ScreenshotImage` whose `data` starts with the JPEG magic bytes `FF D8`, `content_type` `image/jpeg`, and whose `html` matches the same session's DOM. A fixture with `#onetrust-accept-btn-handler` has its banner hidden by the CSS tier.
- **Negative:** `screenshot(url, consent_click=False)` on the same fixture does not run the accept script, so the banner's click handler never fires. The test asserts the handler's side-effect marker is absent.

### Slice 2c — spend and budget

- **Happy:** a run with browser kinds and a local budget API completes its batch, records `browser_seconds_used` in the tally, and the budget API's reserve count is zero (I2).
- **Negative:** when the run's own browser budget is spent, `BrowserSpend` raises `StopDrain("browser_budget", ...)` before the call, and the page is not rendered.

### Slice 2d — pacing

- **Happy:** two sequential renders of different hosts run with no added delay beyond the per-host pacing.
- **Negative:** two renders of the same host run one after the other, never overlapping (I6), even with the browser concurrency set to 4. The test uses a fixture that records start and end times.

## Green

- Implement `LocalPlaywrightBrowser` behind `BrowserClient`. Reuse `CONSENT_HIDE_CSS` and `CONSENT_ACCEPT_SCRIPT` from `browser/consent.py`. Use `GOTO_OPTIONS`, `VIEWPORT` and `JPEG_QUALITY` from `browser/payloads.py`, so there is one source of truth.
- A fused call (HTML and screenshot from one page session) serves `FusedRenderPageHandler`. Keep the fused flag off by default, as today.
- Wire the local provider into `browser_setup.py` behind a `--provider local` switch.
- The local path claims one task per claim (D11) and passes `screenshot_sweep_limit=None` (D10).

## Refactor

- `CloudflareBrowserClient` and `LocalPlaywrightBrowser` both convert a failure to `BrowserRequestError`. If the mapping repeats, extract one helper for the timeout-to-retryable mapping.
- `browser_setup.prepare_browser` gains a provider branch. With two providers a factory is cheaper than the branch; extract `_build_browser(provider)`.
- `browser_spend.py` reads the ledger through the guard. The local path injects the local budget API instead of changing the spend class.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "browser and local" -q
cd apps/discovery-ingest && .venv/bin/python -m ruff check discovery_ingest && .venv/bin/python -m mypy discovery_ingest
```

Then the 50-page comparison from the measurement gate, recorded in the ledger.

## Exit

- The 50-page comparison passes its gate, and the Patchright decision (O5) is recorded with the blocked counts.
- A bounded local render run completes against the live queue. The Cloudflare browser counter does not move.
- The run queued no `capture_screenshot` tasks of its own (D10).
