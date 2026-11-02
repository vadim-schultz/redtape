---
name: Document browse by confidence — Live runs
overview: "The post-deploy read-only run chapter 11 calls for: list latency and S3, filter/sort/search/total checks against the production candidate API, the seeded documents gone, and a headless-Chrome pass over /documents, the menu and the retired routes."
isProject: false
---

# Document browse by confidence — Live runs

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) (S3) · **Architecture:** [00-architecture.md](00-architecture.md) · **Chapter:** [chapters/11-live-validation.md](chapters/11-live-validation.md)

**Who ran this:** a chapter-implementer agent against production (`https://redtape.cc`), 2026-11-02, after the release PR (#324) merged and was deployed. Read-only: `GET`s only, no write call, no data change. Every endpoint used is public, so the probe credential was not needed and was not used. The browser pass is **headless Chrome 155 driven over its DevTools protocol** (no interactive session, no signed-in session); what that could not reach is listed under NOT CHECKED. Screenshots are kept out of the repo.

## LR1 — API

### Latency and S3

**Budget (the chapter's figure, adopted before any result was judged):** p95 of `GET /api/v1/candidates?limit=20` under **1.5 s** end to end from the measuring client (the chapter's suggestion). The client is remote, so every figure includes network and edge: `GET /api/v1/countries`, a trivial read, measured min 0.43 s, median 0.50 s, p95 0.77 s, max 0.83 s over 19 requests, i.e. roughly 0.45 s of that is not the list query.

Total time in seconds, one `curl` per request (a new connection each). Series A and B were the first, exploratory pass; C and D repeated them with a time-to-first-byte split, and the first request of each is reported separately.

| Series | First request | n | min | median | p95 | max |
| --- | --- | --- | --- | --- | --- | --- |
| A: same URL `limit=20`, run 1 (first included) | 0.96 | 20 | 0.80 | 0.98 | 1.33 | 2.55 |
| B: `limit=20`, `offset` 0, 20 … 380 (first included) | 1.46 | 20 | 0.77 | 1.09 | 2.40 | 2.45 |
| C: same URL `limit=20`, run 2 (first excluded) | 0.99 | 20 | 0.84 | 1.13 | 1.41 | 1.47 |
| D: `limit=20`, `offset` 0 … 400, run 2 (first excluded) | 2.67 | 20 | 0.78 | 0.92 | 1.48 | 1.51 |
| **Pooled A to D** | | 80 | 0.77 | 1.01 | **1.74** | 2.55 |

7 of the 80 pooled requests were over 1.5 s. The first request of a series is not systematically slower (0.96, 1.46, 0.99, 2.67 s), so there is no visible cold penalty beyond ordinary variance. Server-side share (time to first byte minus TLS handshake) for series C: min 0.48, median 0.62, p95 0.93, max 1.00 s.

Cost by variant (10 requests each, total time): `sort_by=title` median about 0.80 s, `sort_by=created_at` about 1.0 s, default (confidence) about 1.0 s, `limit=1` about 0.9 s. Isolated 2.2 to 2.7 s outliers appear on every variant, including title sort, roughly once per 10 to 20 requests, and never on `/countries`.

**S3 outcome: over budget on the pooled figure (p95 1.74 s against 1.5 s), so by the chapter's own rule S3 becomes a follow-up.** Individual 20-request series land on both sides of the line (1.33, 1.41, 1.48 and 2.40 s), so the verdict is the pooled one. Caveats for whoever picks it up: the pool is 4,666 rows, the median is about 0.55 s above the trivial-endpoint baseline, and the slow tail shows up on queries that do not order by score, so materialising `candidate_tag_scores` may not remove it. Measure server-side (`EXPLAIN ANALYZE` of the list query, one request's wall time in the API log) before building it. Nothing here blocks the release.

### Functional checks

| Check | Result |
| --- | --- |
| `filter[situation]=<code>`: confidence below 0.4 **and** above 0.7, ordered high to low | **Partial.** Ordering high to low holds for all 18 situation codes (`desc` on every page). The two-band mix does not occur on the situation axis: no situation score below 0.5 exists (values 0.5, 0.567, 0.85, 0.95, 1.0). `new-job` has 9 mid and 2 high, `illness-care` 2 mid and 5 high. On the domain axis `filter[domain]=social-benefits` (20 candidates) has both: one at 0.167 (`0b450866…`, "Bescheid"), 18 at 0.5, one at 1.0 (`2bea6edf…`), ordered 1.0, 0.5 …, 0.167. The shape is a data limit (the LLM curve starts at 0.5), not a defect. |
| Card confidence is filter-aware | **Pass.** For all 18 single-situation filters the card confidence equals that code's confidence on the card (0 mismatches); `filter[situation]=job-loss,new-job` equals the max of the two (0 of 18 mismatches); `filter[domain]=social-benefits&filter[situation]=job-loss` equals the max over both (0 of 14); `filter[domain]=social-benefits` equals that domain's score (0 of 20). |
| `filter[domain]=a,b` total at least each single total | **Pass.** `taxes-finance,work-employment` 52 (31, 21); `vehicles-mobility,social-benefits` 36 (16, 20); `housing,taxes-finance` 31 (0, 31); situations `job-loss,new-job` 18 (15, 11). Each union is at most the sum. AND across axes: `work-employment` and `job-loss` gives 2. |
| Unknown code | **Pass.** `filter[domain]=nope` returns 422. |
| `sort_by=title&sort_order=asc` differs from the default and is alphabetical | **Pass, with a note.** First page differs from the default; it reads Anlage…, Antrag…, Betriebserklärung…, „De-minimis“…, Europäisches… , alphabetical with leading quotes and punctuation ignored (database collation). The same order comes back with `Accept-Language: de`, `en` and `?locale=`: titles sort by German, else English, else key, lower-cased, not by the request locale (the code's `title_expression`; the chapter's "per locale" assumption does not apply). `desc` reverses it. `sort_by=confidence&sort_order=asc` starts at 0.0. |
| `q=<fragment>` finds the document | **Pass for German, multi-locale not checkable.** `q=Kurzarbeit` 9 hits, `q=kurzarbeitergeld` 6 (case-insensitive), `q=Rentenbescheid` 3, `q=Führungszeugnis` 24; `q=fuhrungszeugnis` and `q=zzzqqq` 0 (no diacritic folding, as designed). Identical with `Accept-Language: de` and `en`. All 4,666 titles are identical in the `de` and `en` responses, so no production candidate has a title that exists only in another locale and the "found in more than one locale" case has no data to run on. `q` composes with `filter[situation]` (`Kurzarbeit` and `job-loss`: 2) and with `sort_by=title`. |
| `GET /api/v1/documents` returns `total: 0` | **Pass.** `{"items":[],"total":0,…,"available_leaf_codes":[]}`; the seeded rows are gone. |
| Jurisdictions DE, SN, DD remain | **Pass.** `/api/v1/countries` returns `DE`; `/api/v1/states?country=DE` returns the 16 states including `14` (Sachsen); `/api/v1/districts?state=14` returns `14612` (Dresden, Stadt) and `/api/v1/cities?district=14612` returns `14612000`, the seed's SN and DD codes. |

### Sample used

Total candidates **4,666**. Card confidence over the whole unfiltered pool: **4,570 at 0.0** (no tag at all), 77 at 0.5, 1 at 0.567, 6 at 0.85, 7 at 0.95, 5 at 1.0; none strictly between 0 and 0.4. Codes used: situations `job-loss` (15), `new-job` (11), `illness-care` (7), `buying-vehicle` (7), `starting-school` (7); domains `social-benefits` (20), `taxes-finance` (31), `work-employment` (21), `vehicles-mobility` (16), `housing` (0). Candidate ids used (first 8 characters): `2bea6edf`, `0b450866`, `6aaaefa0` (Kurzarbeitergeld), `3c24a78f` (Rentenbescheid), `4df46465` (Zulassungsantrag, item page). 8 of the 18 situation codes (`marriage`, `separation-divorce`, `going-self-employed`, `studying`, `buying-property`, `getting-licence`, `naturalisation`, `retirement`) and 3 of the 13 domains (`housing`, `retirement-old-age`, `self-employment-business`) have no candidate at all.

## LR2 — Browser (headless Chrome over DevTools protocol)

Screenshots (scratchpad, not committed): `documents-desktop-light.png`, `documents-narrow-light.png`, `yellow-light.png`, `red-light.png`, `yellow-dark.png`, `menu-open.png`, `chip-domain.png`, `chip-group.png`, `chip-sub.png`, `chip-after-reload.png`, `dark-desktop-chips.png`, `dark-narrow-vehicles.png`, `item-page.png`, `suggest.png`.

| Check | Result |
| --- | --- |
| `/documents` renders cards with a circle, desktop 1280 and narrow 390 | **Pass.** 20 cards per page, "4666 documents", pager to 234. |
| Circle colours | **Pass.** Computed SVG strokes: 0 percent red (ring 220,38,38; track 254,202,202); 50 and 57 percent yellow (range 253,224,71, track 254,240,138); 85, 95, 100 percent green (range 22,163,74, track 187,247,208). The range is darker than the track in every band; in dark mode the track darkens (green 18,74,40; yellow 113,63,18) and the range keeps its colour. The `aria-label` names the band ("Confidence 57%, medium"). The 0 percent ring is only the pale track, as there is no value sector. |
| Domain chip selected | **Pass.** Light mode 218,41,28 (swiss red) with white text; dark mode 224,73,62 with dark text. URL `?domain=work-employment`, "21 documents". |
| Life-area chip selected, expands, shows every document of the area | **Pass.** `Work & career` with the domain chip: same red, the situation row expands, "3 documents", `?domain=…&group=work-career`. |
| Situation chip inside it: lighter red, narrows, area chip outline hint | **Pass.** `Losing a job`: 238,157,151 with dark text and a red border (dark mode 233,129,121); URL swaps `group` for `situation=job-loss`; "2 documents"; `Work & career` becomes transparent with red text and a border. |
| Search, sort, order toggle and pager keep the chips; offset resets; reload keeps state | **Pass.** `domain=taxes-finance` (31), page 2 keeps the chip (`offset=20`, 11 cards); search `Antrag` drops `offset` (15); sort Title and toggling to desc update the URL and the order (first card "Zulassungsantrag" in desc); reloading the full URL restores the chips and the sort. The sort menu offers Confidence, Title, Newest. |
| Empty state | `domain=vehicles-mobility&situation=moving-house`: "No documents found" with "Clear filters". |
| Menu (desktop and 390 px wide, light) | **Pass.** Items are Home (full width, centred, with icon), Profile, Documents, Colour mode, Language. No Suggest and no Candidates link. Clicking Home, Profile (`/login`), Documents and a language flag (EN, DE) each closes it; the colour switch toggles the theme and keeps it open. |
| `/candidates` redirects | **Pass.** Lands on `/documents`. |
| `/candidates/<id>` opens the item page and Back returns to the filtered list | **Pass.** Item page title "Zulassungsantrag"; `history.back()` returned the identical URL (`domain`, `sort_by=title`, `sort_order=desc`, `q`) with the same 15 cards and chip state. |
| `/suggest` not-found page | **Pass.** "Page not found / This address is not part of Redtape. / Browse Documents". |
| Dormant routes | `/suggestions` still renders (public list with 2 pending suggestions); `/documents/<unknown id>` shows "Document not found". As designed (D1, D3). |

### NOT CHECKED

- **Sign out** closing the menu, and the discovery admin links closing it: needs a signed-in session.
- **Touch behaviour**: the menu would not open under CDP mobile emulation with synthetic mouse events (not a finding, a limit of the harness); touch interaction on a real phone is unchecked. The 390 px menu was checked with a narrow desktop window.
- **Hover, focus and keyboard states** of chips, menu items and the pager beyond one default screenshot.
- **Real-device rendering**: one engine (Chrome 155) only; no Safari or Firefox.
- **Multi-locale search** (title only present in a non-German locale): no such data in production.
- **Pixel-level colour judgement of the value sector** at 100 percent: the ring is fully covered, the track is not visible; judged from computed colours instead.

## Observed findings

Not fixed here; for a follow-up.

1. **Percentage label sits outside the ring.** In every screenshot the `ValueText` ("57%") is at the upper right of the 32 px circle, not inside it. Cosmetic.
2. **98 percent of the list is 0 percent.** 4,570 of 4,666 candidates carry no tag, so unfiltered and with no search they show a red 0% circle; only 96 are tagged. Default order puts the tagged ones first, so page 1 is meaningful, but pages 5 to 234 are all 0%. Expected from invariant 1 (nothing is hidden), and worth a decision on whether an untagged document should show a circle at all.
3. **Latency tail** (S3 above): median 1.0 s end to end, occasional 2.2 to 2.7 s on every variant.
4. **Title sort ignores the request locale** and sorts by the German title, else English, else key; "alphabetical per locale" in the chapter is not what is implemented.
5. **Dark mode: unselected chips have no visible pill.** Their fill (24,24,27) equals the card, so only the label shows; selected states are fine.
6. **Dark mode: selected domain chip uses dark text on lighter red** (24,24,27 on 224,73,62), unlike white on red in light mode. Readable; a visual inconsistency, not a failure.
7. **Situation scores cannot be low today.** The scorer floors a single LLM mention at 0.5, so the "low and high in one situation filter" case never occurs in production data; low circles on a situation filter would need weaker evidence than any now stored. Not a calibration change (D2 stands).
8. **Home goes to `/documents`**: the Home link's `href` is `/`, which lands on the documents page. Expected after the redirect, noted for completeness.
9. **`/suggestions` stays public** and lists 2 pending suggestions with no link to it from the menu (D3, S5).

## Verdict

Shipped behaviour matches the contract: presence-based filters, filter-aware card confidence, CSV filters, sort, search and totals, seeded documents gone with DE, SN and DD intact, circles and chips in the right colours, menu closing on select, retired routes behaving. Open: S3 becomes a follow-up (pooled p95 1.74 s against the 1.5 s budget), and the NOT CHECKED list above needs a person or a signed-in session.
