---
name: "Candidate view polish — Architecture"
overview: "Five small, independent fixes to the public candidate item page and the app shell found on review: tiered cookie-consent dismissal before the evidence screenshot is captured, a full-height scrollable screenshot instead of a cropped one, plain-language ingress/egress headings, the sources list behind a collapsed accordion, and a sitewide body panel so every page's content is visually distinct from the canvas."
isProject: false
---

# Candidate view polish — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/) · **Parent:** [candidate-view](../candidate-view/00-architecture.md)

## 1. Why

A review of `/candidates/:id` (the candidate-view suite's item page) found five issues, none of which need new infrastructure or data-model changes:

1. The evidence screenshot sometimes shows an uncollapsed cookie-consent banner across the top, which looks bad as evidence and isn't the real page.
2. The screenshot is captured full-page but displayed cropped to a fixed 16:10 box, so a tall source page is invisible below the first viewport.
3. The ingress/egress section headings use the graph terms themselves ("Ingress"/"Egress"); the plain-language phrasing the candidate-view suite already wrote (D2 there) lives only in an unused subtitle line.
4. The sources list (the procedure pages that back the candidate) is always visible, which exposes bureaucratic-process framing on a site that is meant to be document-focused, not process-focused.
5. No page in the app visually distinguishes its body content from the surrounding canvas — every page sits directly on `bg.canvas`, even though the design tokens already have a separate `surface.base`/`border.base`/shadow set for exactly this.

This suite is five chapters, independent of each other, fixing each in place. It does not change what data is captured, stored or served — only how the screenshot is captured (tiering), and how existing data is presented.

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Consent tier** | One of three escalating, best-effort steps taken before a Cloudflare Browser Run screenshot capture to keep a cookie/consent banner out of the image: hide by CSS (tier 1), click an accept button by script (tier 2), detect-and-flag after the fact (tier 3). None of the tiers retries the capture or adds a scripted session — they are fields on the existing single-shot request. |
| **Body panel** | A `surface.base` container with `border.base` and a shadow token, wrapping a routed page's content inside `AppLayout`, distinct from the `bg.canvas` page background around it. |
| **Ingress / Egress** | Unchanged from [candidate-view](../candidate-view/00-architecture.md) D2: ingress is what a candidate requires, egress is what requires it. This suite changes only which string is the heading, not the direction, the data or the internal `kind: "ingress" | "egress"` prop. |

## 3. D1 — Screenshot consent tiering (ingest)

Capture today: `CloudflareBrowserClient.screenshot()` (`apps/discovery-ingest/discovery_ingest/browser/client.py`) calls the Cloudflare Browser Run `/snapshot` quick action with `snapshot_body(url, user_agent, ["content", "screenshot"])` (`apps/discovery-ingest/discovery_ingest/browser/payloads.py`). The request body carries only `url`, `gotoOptions`, `userAgent`, `viewport`, `screenshotOptions` — no interaction with the page before the screenshot is taken. Cookie/consent-widget handling exists only for the *text* extraction path (`apps/discovery-ingest/discovery_ingest/extract/clean_dom.py:13`, `WIDGET_NAME = re.compile(r"(?<![a-z])(?:cookie|consent|search|breadcrumb)")`), stripped from the DOM after capture — it never touches the image.

Cloudflare's Browser Run REST body already accepts, alongside the fields already sent, `addStyleTag` and `addScriptTag` entries that run in the page before the screenshot. The three tiers below are additive fields on the same single request, not a new call or a scripted multi-step session:

- **Tier 1 — hide by CSS (always on).** An `addStyleTag` with a small stylesheet of curated selectors for the handful of CMPs that account for most consent banners (OneTrust `#onetrust-banner-sdk`/`#onetrust-consent-sdk`, Cookiebot `#CybotCookiebotDialog`, Quantcast/Didomi `#qc-cmp2-container`/`#didomi-host`, Osano `.osano-cm-window`) plus a few generic attribute patterns (`[class*="cookie-banner" i]`, `[id*="cookie-consent" i]`, `[aria-label*="cookie" i]`), each `display: none !important`. Cheapest, broadest, works even on a banner that is a pure overlay with no accessible "accept" control.
- **Tier 2 — click accept by script (best effort).** An `addScriptTag` with a short script that, after DOM content is ready, looks for a known "accept all" button for the same CMPs (OneTrust `#onetrust-accept-btn-handler`, Cookiebot's allow-all button id, Didomi's agree button id, etc.) or a generic text match (accept/agree/allow/consent, in English and German) across buttons and links, and clicks the first match. A short settle wait follows so any closing animation finishes before the screenshot. This is a real dismissal, not just a visual hide, so it is tried in addition to tier 1, never instead of it — tier 1 is the guaranteed fallback if the click misses or targets the wrong element.
- **Tier 3 — detect and flag (observability, not a retry).** Cloudflare's `/snapshot` call already returns the rendered `content` (DOM) in the same response as the `screenshot`. Reuse `clean_dom.py`'s existing `WIDGET_NAME` pattern against that returned DOM to check whether a consent-widget node is still present after tiers 1–2. When it is, log/record the fact (a counter or a log line, not a new column) rather than blocking ingestion or retrying — the REST quick action is a single fire-and-forget call, there is no session to retry mid-page. This surfaces banners that slipped through tiers 1–2 for manual follow-up (an expanded selector list) without holding up the pipeline.

No Cloudflare Worker, no Puppeteer/Playwright binding, no new billing surface is introduced (per the user's choice of the lighter option).

## 4. D2 — Full-height scrollable screenshot (web)

`CandidateScreenshot.tsx`'s `ScreenshotFrame` (`apps/web/src/features/candidates/components/CandidateDetailView/CandidateScreenshot.tsx`) wraps the `<img>` in a `Box` with `aspectRatio={16/10}` and `overflow="hidden"`, and the image itself uses `objectFit: "cover"`/`objectPosition: "top"` — a tall full-page capture is clipped to its first viewport with no way to see the rest. The fix replaces the fixed-aspect-ratio crop with a fixed **max-height** box (`overflowY: "auto"`, `overflowX: "hidden"`) and the image at natural size (`width: 100%`, `height: auto`, no `objectFit`), so the full captured page is reachable by scrolling inside the frame rather than clipped.

## 5. D3 — Plain-language ingress/egress headings (web)

`NeighbourSection.tsx` (`apps/web/src/features/candidates/components/CandidateDetailView/NeighbourSection.tsx`) renders a heading (`candidates.ingress`/`candidates.egress`, currently "Ingress"/"Egress") **and** a separate subtitle line (`candidates.ingress_subtitle`/`egress_subtitle`, already "Documents you need first"/"Documents that need this one" in `en.json`, and the German equivalents in `de.json`) directly below it. The plain-language copy the user wants already exists — it's one line too low. The fix promotes the subtitle text to the heading itself and drops the now-redundant subtitle line (and its i18n keys) from the component; the internal `kind: "ingress" | "egress"` prop and the candidate-view suite's D2 vocabulary are untouched — this is a presentation change in one component plus the two locale files (`en`, `de`, the only two fallback locales that exist).

## 6. D4 — Sources behind a collapsed accordion (web)

`CandidateEvidence.tsx` renders `CandidateSources` directly beneath the screenshot, under the shared "Evidence" heading, with no heading of its own — the sources (procedure title, portal link, role badge, excerpt) are always visible. The `candidates.sources` i18n key ("Sources"/"Quellen") already exists but is unused. The fix wraps `CandidateSources` in a Chakra v3 `Accordion`, collapsed by default, titled with that existing key. This is the first use of `Accordion` anywhere in `apps/web/src` (confirmed by a repo-wide search). The sources data itself, and what it contains, is unchanged — this only defers when it's shown, per the user: the site is document-focused, not process-focused, and this information may resurface later when browsing by domain/life-situation is built.

## 7. D5 — Sitewide body panel (web)

`AppLayout.tsx` (`apps/web/src/components/layout/AppLayout.tsx`) wraps every routed page's content (`{children}`) in a `Box as="main"` and a `Container`, both on `bg.canvas` — identical to the outer page background, so there is no visual boundary between "page" and "page content" anywhere in the app. The theme already distinguishes `surface.base`/`border.base`/the `shell` shadow token from `bg.canvas` (used today only by `SectionCard`, for individual admin sections, never for a whole page body). The fix wraps `{children}` inside `AppLayout` in a panel using those same tokens — same visual language as `SectionCard`, applied once, at the single shell integration point, so it reaches every page without touching individual page components. Left open (see [gaps-and-decisions.md](gaps-and-decisions.md)): whether any page should be able to opt out of the panel.

## 8. Non-goals

- No change to the `ingress`/`egress` data model, edge direction, or the candidate-view suite's D2.
- No change to what sources data is stored or how it's computed — only when it's shown.
- No Cloudflare Worker or Puppeteer/Playwright binding; consent tiering stays inside the existing single-shot REST request.
- No resolution of the AppLayout opt-out question — left to chapter 5 (or a later chapter) to decide while implementing.
- No new locales beyond the two that already exist (`en`, `de`).
