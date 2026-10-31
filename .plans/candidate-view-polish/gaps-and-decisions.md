---
name: "Candidate view polish — Gaps and decisions"
overview: "Settled decisions for consent tiering, the scrollable screenshot, the plain-language headings, the sources accordion and the body panel; open seams and risks."
isProject: false
---

# Candidate view polish — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

Decisions D1 and D5's mechanism were made by the owner on 2026-10-31 (session Q&A); the rest follow from the request and the exploration. Do not re-open them during implementation.

| # | Decision |
| --- | --- |
| D1 | **Consent tiering stays on the existing single REST request.** `addStyleTag` (tier 1, always on) and `addScriptTag` (tier 2, best effort) are added as fields on the existing `/snapshot` call; tier 3 is detection-and-flag only, reusing `clean_dom.py`'s `WIDGET_NAME` pattern against the DOM the same call already returns. No Cloudflare Worker, no Puppeteer/Playwright binding, no retry loop. Reason: the owner chose the lighter option over new scripted-session infrastructure. |
| D2 | **The curated CMP selector/script list is a starting set, not exhaustive.** Tier 1 and tier 2 cover the handful of CMPs that account for most consent banners (OneTrust, Cookiebot, Quantcast/Didomi, Osano) plus a generic attribute/text-match fallback. It will need expanding as new banners are observed in the wild; tier 3's flag is what surfaces that need. |
| D3 | **Tier 3 is observability, not a gate.** A screenshot with a detected leftover banner is still stored and served; the flag is a log line or counter for follow-up, not a blocker, a retry, or a new database column. Keeps this suite behaviour-preserving on the capture pipeline's data model. |
| D4 | **The screenshot frame scrolls; it does not resize to fit.** A fixed max-height box with `overflowY: auto` is simpler and more predictable across screen sizes than sizing the box to the image's own (variable) aspect ratio. The image keeps its natural aspect ratio inside the box (no `objectFit`). |
| D5 | **Ingress/egress heading promotion is a presentation-only change.** The internal `kind: "ingress" | "egress"` prop, the API's `ingress`/`egress` field names, and the candidate-view suite's D2 vocabulary are unchanged — only the heading string (and the now-redundant subtitle line) changes. Scope is `NeighbourSection.tsx` plus `en.json`/`de.json`. |
| D6 | **The sources accordion is collapsed by default, on every visit.** No "remember last state" persistence (no reason yet to add one); per the user, the goal is to not expose process framing by default, not to let a returning visitor reopen it automatically. |
| D7 | **The body panel is bundled into this suite, not a separate suite.** Although it affects every page, it is one component change (`AppLayout.tsx`) with low risk, and the owner chose to keep it with the review that surfaced it rather than spinning up a second suite. |
| D8 | **The body panel reuses `SectionCard`'s token set, not new tokens.** `surface.base`, `border.base`, and the `shell` (or `card`) shadow token already exist and already express exactly this "raised panel" look; chapter 5 does not add new semantic tokens. |

## Open seams

- **AppLayout opt-out.** Whether some pages (e.g., a wide admin table or data-heavy screen) should be able to render without the body panel's padding/surface is not decided here. Default for v1: no opt-out, every page gets the panel uniformly; chapter 5 can add a prop later if a page genuinely needs to go full-bleed.
- **Tier-3 flag surface.** Where the "banner still detected" signal is recorded (a structured log field vs. a simple counter) is left to the chapter author; no new table or column is in scope for this suite.
- **CMP coverage.** The curated selector/script lists in tiers 1–2 cover the most common CMPs observed in general web crawling, not a survey of this project's actual source portals. Expect to extend the list after the first live screenshots are reviewed.
- **Locale scope.** Only `en` and `de` exist today (`i18n/fallback/`); D5 (heading promotion) and D6 (accordion title) only need those two.
- **Process information re-exposure.** Collapsing the sources list (D6) does not delete or hide the underlying data from any future domains/life-situations browsing view — this suite only changes the candidate detail page's default disclosure state.

## Risks

| Risk | Mitigation |
| --- | --- |
| Tier 2's generic text-match accept-button click mis-clicks something unrelated on an unfamiliar page | Tier 1's CSS hide runs regardless, so even a bad click still leaves the banner visually hidden; tier 2 only adds named CMP selectors plus a narrow text match, not a blind "click the first button" |
| A real page genuinely needs edge-to-edge layout and looks wrong inside the new body panel | Flagged as an open seam (AppLayout opt-out); chapter 5's manual smoke should look at a representative admin table page before merging |
| Dropping the ingress/egress subtitle line removes context some users relied on | The promoted heading *is* that same text — no information is lost, just moved up one line |

## Out of scope

Any change to the candidate-view suite's data model, API contract, or ingress/egress edge direction; any change to what sources data is captured or computed; a Cloudflare Worker or Puppeteer/Playwright migration; a domains/life-situations browsing view (future work that may reuse the now-collapsed sources data); new locales; persisted user preference for the accordion's open/closed state.
