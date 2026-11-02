---
name: "Chapter 11 — Live validation"
overview: "After the release is deployed, check the shipped change on redtape.cc: list latency with the live score model, chips showing low-confidence documents, circle colours at real scores, menu behaviour in a real browser, and the seeded documents gone."
todos:
  - id: wait-for-deploy
    content: "Confirm chapters 1-10 are on main and deployed"
    status: pending
  - id: api-checks
    content: "Measure /api/v1/candidates latency; check filters, sort and totals"
    status: pending
  - id: ui-checks
    content: "Browse /documents in a real browser: chips, circle colours, search, sort, paging, menu"
    status: pending
  - id: seed-check
    content: "Confirm no seeded documents and the DE/SN/DD jurisdictions remain"
    status: pending
  - id: record
    content: "Write 02-live-runs.md and resolve or open S3"
    status: pending
isProject: false
---

# Chapter 11 — Live validation

**Repo:** `redtape` · **Branch:** none (read-only measurement, as in the earlier suites) · **Status:** planned
**Depends on:** the release PR merged to `main` and deployed · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

Local tests prove the code; this proves the shipped behaviour on real data, and settles seam S3 (cost of computing the score model on every list request). Result goes into `02-live-runs.md` (LR1) in this suite folder, and into `gaps-and-decisions.md` (S3 resolved or turned into a follow-up).

## Method

Production access follows the earlier suites: `/home/schult_v/.config/redtape/probe.env`, sourced and never printed. No write calls. The checks are read-only `GET`s plus a browser pass.

### LR1 — API

| Check | Expected |
| --- | --- |
| `GET /api/v1/candidates?limit=20` timed 20 times, cold and warm | p95 under the budget set before the run (suggest 1.5 s; record the figure); if over, S3 becomes a follow-up to materialise `candidate_tag_scores` |
| `filter[situation]=<one code>` returns candidates whose card confidence for that code is below 0.4 as well as above 0.7 | both present, ordered high to low by default |
| `filter[domain]=a,b` total ≥ each single total | holds |
| `sort_by=title&sort_order=asc` first page differs from the default order and is alphabetical per locale | holds |
| `q=<a known title fragment>` | the document is found, in any locale |
| `GET /api/v1/documents` | `total: 0` (seeded rows gone); jurisdictions DE, SN, DD still exist (`GET /api/v1/countries` or the equivalent) |

### LR2 — Browser

Real browser (desktop and a narrow viewport), light and dark:

- `/documents` shows cards with a circle; ring and value colours are red below 40%, yellow 40–69%, green from 70%; the value sector is visibly darker than the ring.
- Selecting a life-area chip is bright red and shows every document of the area; opening it and selecting a situation turns that chip a lighter red and narrows the list; the area chip shows the outline hint.
- Search, sort and the pager keep the chips; reload keeps the state (URL).
- Menu: Home is centred; clicking Home, Documents, a profile link, and Sign out each closes it; the colour switch keeps it open; the language flag closes it; there is no Suggest and no Candidates link.
- `/candidates` lands on `/documents`; `/candidates/<id>` opens the item page and Back returns to the filtered list.
- `/suggest` shows the not-found page.

Record any rough edge as an `observed` finding, not a fix.

## Result

Write `02-live-runs.md` with the measured figures, the sample candidates used, screenshots' file names (not committed), and the S3 outcome.

## Out of scope

Fixes (open a follow-up suite or chapter); any data write; re-calibrating the confidence bands (D2).
