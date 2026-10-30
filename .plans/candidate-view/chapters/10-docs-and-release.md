---
name: "Chapter 10 — Docs and release"
overview: "Synchronise the documentation with the new public routes and screens, write the operator doc with the release smoke checklist and the screenshot cadence, update the plan indexes, and prepare the release."
todos:
  - id: operator-doc
    content: "docs/operations/candidate-view.md: routes, deploy order, screenshot cadence, release smoke checks"
    status: pending
  - id: route-tables
    content: "discovery-layer.md route table and the web route surface list the new routes and the machine sources route"
    status: pending
  - id: indexes
    content: "Plans README, STATUS, loop doc and admin-tables.md point at the new suite and tables"
    status: pending
  - id: docs-tests
    content: "A docs test pins the new links and the smoke checklist headings"
    status: pending
isProject: false
---

# Chapter 10 — Docs and release

**Repo:** `redtape` (docs, `apps/api/tests`) · **Branch:** `docs/candidate-view-release` · **Status:** planned  
**Depends on:** [07-flow-diagram.md](07-flow-diagram.md), [09-catalogue-vs-coverage.md](09-catalogue-vs-coverage.md) and the live runs LR1 and LR2 in [../02-live-runs.md](../02-live-runs.md) (their totals and the showcase list go into the operator doc) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

The repository documents what now exists, an operator can deploy and verify it, and a human can run the manual smoke that no agent could (the harmonization suite shipped without it for lack of a browser; this suite records that gap honestly again if it recurs).

## Contract

1. **`docs/operations/candidate-view.md`** (new). Sections: *What it is* (public, read-only, unreviewed, completeness model in one table); *Routes* (web `/candidates`, `/candidates/:id`; API `GET /api/v1/candidates`, `/{id}`, `/{id}/screenshot` with the cache and 503 behaviour; machine `GET /machine/candidates/sources`); *Deploy order* (API first, no migration, then web; the public pages need both); *Screenshot cadence* (how to repeat the drain of [02-live-runs.md](../02-live-runs.md): one UTC day's 570 browser seconds, about 55 to 65 pages, record the live-run totals from the ledger); *Showcase candidates* (the list from the ledger with their `/candidates/<id>` paths and roles, the curation file path `docs/operations/candidate-curation/showcase.json`, what `manual` means for tags and edges, and the **reversal SQL**: delete `discovery_candidate_edge` rows with `extractor = 'manual'`, then `discovery_candidate_mention` rows with `extractor = 'manual'`, then staged candidates left without a mention, with a `SELECT count(*)` of each first); *Exposure and the open curation seam* (unreviewed output, the banner, the hide-list follow-up); *Release smoke checks* (below).
2. **Release smoke checks** (a heading `## Release smoke checks` in that file, the anchor the ledger links to). Each item has a status line (`not yet performed` until a human ticks it):
   - The showcase candidates (named in the doc) are at the top of `/candidates` with five present chips, and each opens with tags on both axes, ingress and egress cards as designed, the diagram and a screenshot. Check the roles of the set: both-sided, ingress-only, egress-only, many neighbours (or the cap note), long title (tooltip).
   - `/candidates` lists candidates, complete ones first; each card shows its completeness chips; the "complete only" switch, search, domain and situation chips and paging reset to page one; empty and error states are readable.
   - `/candidates/:id` shows title, description with its source attribution, ingress and egress cards, the flow diagram (arrows converge on the title card and diverge to the egress cards), the screenshot, and the sources; a candidate without edges shows the "no dependencies staged" note; a reload of the screenshot is a 304.
   - Light, dark and narrow (below `md`) layouts: the diagram is hidden below `md` and the card lists remain; focus rings, link names and the diagram's text alternative are present.
   - The menu has a Candidates icon link for everyone, not only admins.
   - `/admin/discovery/documents`: toolbar in the table header; every column sorts; filters appear as removable chips; the Ready quick filter works; a long title is clipped and its tooltip shows the whole text on hover and on keyboard focus.
   - `/admin/discovery/catalogue` and `/coverage` show different top blocks; catalogue chips filter the table; coverage is unchanged.
3. **Route tables.** `docs/operations/discovery-layer.md` (route table near the admin and machine routes, and the web admin route surface) lists the machine sources route and links the operator doc; `docs/operations/admin-tables.md` notes the header toolbar, the bounded cell and the catalogue stage filter and sort; the extraction operator checklist's screenshot line (OP9) links the requeue command.
4. **Indexes.** `.plans/README.md` gets the `candidate-view` section with the status line; `docs/planning/STATUS.md` gets one dated update line (public candidate view built on the loop branch, release PR pending); `docs/operations/loops/candidate-view.md` status moves to built; the ledger release checklist is complete except the human smoke and the deploy.
5. **Docs test.** One test in `apps/api/tests/test_discovery_docs_sync.py` (same style as the existing ones) asserts that `candidate-view.md` exists, contains the headings `## Release smoke checks` and `## Deploy order`, that every relative link in it and in the suite's `00-architecture.md`, `01-rollout.md`, `02-live-runs.md`, `gaps-and-decisions.md` and `run-ledger.md` resolves, and that `.plans/README.md` links the suite. A negative case: the test names the broken link in its failure message when one is missing (assert on a deliberately broken temp copy through the helper functions already in the file).
6. **Release.** The chief of staff opens the release PR from the loop branch to `main` after verifying every chapter PR merged on the host. Remote CI runs if Actions minutes are back (about 2026-11-01); otherwise the local gate on the loop branch is recorded.

## Red tests

| Test | Asserts |
| --- | --- |
| `candidate view operator doc links resolve` | The doc exists and its relative links resolve. |
| `candidate view operator doc has the deploy order and smoke headings` | Both headings are present. |
| `plans readme links the candidate view suite` | The index names the suite and its rollout. |
| `suite documents have no broken relative links` | The five suite files resolve their links. |
| Negative: `link checker reports the missing target` | The helper, given a temp doc with one broken link, fails naming that link. |

## Green

Write the operator doc and the smoke list, update the route tables and indexes, add the docs tests, copy the live-run totals and the showcase list from the ledger (or write "not collected: blocker" if a live run is deferred, naming the blocker).

## Refactor gate

Audit `test_discovery_docs_sync.py` (it already has a link helper and per-doc constants; add the new doc as data, not a copy of the logic) and the operator doc for duplicated route tables (link to the single table in `discovery-layer.md` instead of repeating it). Report the outcome.

## Verification

```bash
cd apps/api && pytest tests/test_discovery_docs_sync.py && cd ../..
cd apps/web && npm run lint && npm run format:check && npm run typecheck && npm run build && cd ../..
./ci.sh
```

## Commits

`test(docs): pin the candidate view operator doc and links`, `docs: document the public candidate view and its release smoke checks`.

## Out of scope

Performing the manual smoke (a human does), deploying, reviewing candidate quality, changing code outside the docs test.
