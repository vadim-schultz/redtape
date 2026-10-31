---
name: "Chapter 1 — Screenshot consent tiering"
overview: "Three escalating, best-effort steps added to the existing single Cloudflare Browser Run /snapshot request so an evidence screenshot does not show an uncollapsed cookie-consent banner: an always-on CSS hide of known banner selectors, a best-effort script click of a known accept button, and a post-hoc detection flag reusing the existing cookie/consent widget pattern."
todos:
  - id: selectors
    content: "Curated CSS selector list for known CMP banners, sent as addStyleTag"
    status: pending
  - id: accept-script
    content: "Curated accept-button selectors plus a generic text-match fallback, sent as addScriptTag"
    status: pending
  - id: detect-flag
    content: "Post-hoc detection over the returned DOM, reusing clean_dom.py's WIDGET_NAME, logged not blocked"
    status: pending
isProject: false
---

# Chapter 1 — Screenshot consent tiering

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/candidate-view-polish-consent-tiering` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view-polish` · **Release branch:** `main`

## Goal

`CloudflareBrowserClient.screenshot()` sends a `/snapshot` request (`snapshot_body(url, user_agent, ["content", "screenshot"])`) with no interaction with the page before capture, so a cookie/consent banner visible on first load appears in the stored image. Add three tiers to the same request — never a new call, never a scripted session — that keep the banner out of the picture as reliably as a single-shot capture allows, and flag the rare case that still gets through.

## Design decisions

- **Tier 1, CSS hide, always on.** `payloads.py`'s `snapshot_body` gains an `addStyleTag` entry whose `content` is a small stylesheet: selectors for the handful of CMPs that account for most consent banners (OneTrust `#onetrust-banner-sdk`, `#onetrust-consent-sdk`; Cookiebot `#CybotCookiebotDialog`; Quantcast/Didomi `#qc-cmp2-container`, `#didomi-host`; Osano `.osano-cm-window`) plus generic attribute patterns (`[class*="cookie-banner" i]`, `[id*="cookie-consent" i]`, `[aria-label*="cookie" i]`), each rule `display: none !important`. The selector list is a named constant, not inlined in the payload builder, so chapter authors extending it later touch one place.
- **Tier 2, accept-click, best effort.** A second field, `addScriptTag`, carries a short script (also a named constant, built once) that runs after DOM content loads: it tries a known "accept all" button id for the same CMPs, falling back to a generic scan of buttons and links for accept/agree/allow/consent text (English and German), and calls `.click()` on the first match it finds. No error if nothing matches — the script is defensive (wrapped so a thrown error inside it cannot fail the whole request). Tier 1 still applies regardless of whether tier 2's click fires, so a missed or wrong click never leaves a visible banner.
- **Settle wait.** `gotoOptions` keeps `waitUntil: networkidle2`; add a short additional wait (`waitForTimeout`, a few hundred milliseconds) after the script runs and before the screenshot, so any closing animation the accept click triggered has finished. Keep it short enough not to meaningfully change capture latency or the 11-second throttle interval.
- **Tier 3, detect and flag, not a gate.** The `/snapshot` response already returns `content` (the DOM) alongside `screenshot` in one payload. After `_screenshot_image` decodes the image, run the existing `clean_dom.py` `WIDGET_NAME` pattern (`cookie|consent|search|breadcrumb`, applied narrowly here to cookie/consent node names only — do not also match `search`/`breadcrumb`, which are unrelated to this check) against the returned `content` to see whether a consent-widget-like node is still present. When it is, log it (a single structured log line with the url) — never raise, never block, never retry. This chapter does not add a database column or a new table; the signal is for a human reviewing logs to notice a banner that slipped through tiers 1–2, so the selector/script lists (decision D2 in [gaps-and-decisions.md](../gaps-and-decisions.md)) can be extended later.
- **No behaviour change to `render()` or the text-extraction path.** `clean_dom.py`'s existing stripping for extraction is untouched; chapter 1 only reads its pattern, it does not call into or modify `clean_dom.py`'s cleaning function.

## Files

**Edit**

- `apps/discovery-ingest/discovery_ingest/browser/payloads.py` (`snapshot_body` gains the two new fields; the selector CSS and the accept-click script become named module-level constants, or a new sibling module `consent.py` if the constants make this file exceed its size limit)
- `apps/discovery-ingest/discovery_ingest/browser/client.py` (`screenshot()` passes the decoded `content` through the tier-3 check and logs the result; the image/HTML it returns to callers is unchanged)

**Do not edit**

- `apps/discovery-ingest/discovery_ingest/extract/clean_dom.py`'s cleaning behaviour (its `WIDGET_NAME` pattern is read, not changed)
- `endpoints.py`, `images.py`, `classify.py`, `throttle.py`, `usage.py`
- The `render()`/`content` quick action (consent tiering is for the screenshot path only)
- Any database model or migration

## Red tests

`apps/discovery-ingest/tests/test_browser_payloads.py` and `tests/test_browser_client.py` (extend, or create if the narrow payload/client tests don't already exist under those names — check first).

| Test | Asserts |
| --- | --- |
| `snapshot_body includes the consent-hide stylesheet` | Happy: `addStyleTag` is present with content containing at least the OneTrust and generic cookie-banner selectors. |
| `snapshot_body includes the accept-click script` | Happy: `addScriptTag` is present with content that references a known CMP accept-button id and a generic text-match fallback. |
| `snapshot_body keeps the existing fields unchanged` | Negative: `url`, `gotoOptions`, `userAgent`, `viewport`, `screenshotOptions`, `formats` are byte-identical to today's output aside from the two new fields — no accidental change to an existing field. |
| `screenshot() logs when a consent widget is still present` | Happy: a fake response whose `content` contains a node matching the cookie/consent pattern results in one log record, and the method still returns the `ScreenshotImage` normally (not raised, not altered). |
| `screenshot() logs nothing when no consent widget is present` | Negative: a fake response with clean `content` produces no such log record. |
| `tier-3 detection does not match unrelated search/breadcrumb nodes` | Negative: `content` containing a `search`- or `breadcrumb`-named node and nothing cookie/consent-named does not trigger the flag (the narrowed pattern, not the full `clean_dom.py` one, is what's checked here). |
| `a script error inside the page does not fail the request` | Negative: the client's handling of the response is unaffected by whether the injected script succeeded or threw inside the browser — this chapter cannot observe that directly (no real browser in tests), so assert instead that the script constant is wrapped in a try/catch so a page-side failure cannot surface as an HTTP error from Cloudflare. |

## Green

1. Write the named CSS and script constants (or `consent.py` module) with the curated selector lists.
2. Add the two fields to `snapshot_body`; keep the existing fields' shape unchanged.
3. Add the settle wait to `gotoOptions`/the request shape per Cloudflare's accepted fields.
4. Add the tier-3 check in `client.py`'s `screenshot()` path, using a narrowed cookie/consent-only pattern (reusing `clean_dom.py`'s regex building block, not calling its cleaning function).
5. Wire logging; confirm it never raises or changes the returned `ScreenshotImage`.

## Refactor gate

Audit `payloads.py` and `client.py`: the selector/script constants are named and documented with one line each on which CMPs they cover (not inlined string literals scattered through the function); `screenshot()`'s tier-3 check is a small named helper, not inlined in the method; no function grows past the file's existing size discipline. Report what was extracted or "audited, nothing needed".

## Verification

```bash
cd apps/discovery-ingest && pytest tests/test_browser_payloads.py tests/test_browser_client.py
cd ../.. && ./ci.sh
```

## Commits

`test(ingest): define the consent-tiering request fields`, `feat(ingest): hide and click known consent banners before capture`, `test(ingest): flag a leftover consent widget after capture`, `feat(ingest): log consent widgets detected after tiers 1-2`.

## Out of scope

A Cloudflare Worker or Puppeteer/Playwright binding; retrying a capture that still shows a banner; a database column or table for the tier-3 flag; expanding selector coverage beyond the starting CMP list (open seam, [gaps-and-decisions.md](../gaps-and-decisions.md)); any change to the text-extraction cleaning path.

## Git workflow

```bash
git checkout feat/plans-candidate-view-polish && git pull
git checkout -b feat/candidate-view-polish-consent-tiering
```

Open the chapter PR into `feat/plans-candidate-view-polish`.
