# Candidate view: operator guide and release smoke checks

The public candidate view lists the staged document candidates of the extraction suite and opens
each one with its dependencies, a flow diagram and a screenshot of the source page. Since the
[document-browse-confidence](../../.plans/document-browse-confidence/00-architecture.md) suite, the
candidate API is the one document list: it backs `/documents`. This guide covers the routes, the
browse contract, the deploy order, the screenshot cadence, the hand-completed showcase candidates,
the exposure risk and the release smoke checks. Plans and decisions:
[`.plans/candidate-view/`](../../.plans/candidate-view/00-architecture.md) and
[`.plans/document-browse-confidence/`](../../.plans/document-browse-confidence/gaps-and-decisions.md).

## What it is

The view is public and read-only. Anyone can open it without a login. It shows candidate records,
ranked by category confidence and the internal ranking model. It never emits, votes, moderates or
edits. A candidate is listed whether or not it was ever emitted, voted or promoted: those steps are
dormant (see [discovery-layer.md](discovery-layer.md#emit-vote-and-promote-are-dormant)).

Completeness is an internal four-flag read model. A candidate is `complete` when all four are true.
The flags remain available to the API's operational filtering and ranking paths, but they are not
included in the public card/detail response and are not rendered as a banner, checklist, count, or
other user-facing disclosure. The public confidence circle remains the indirect confidence signal.

| Flag | True when |
| --- | --- |
| `has_category` | At least one canonical category code (the tag consensus, or a `manual` code). |
| `has_edges` | At least one staged edge has the candidate as parent or as required end. |
| `has_snapshot` | A procedure that mentions the candidate has an `html_snapshot`. |
| `has_screenshot` | A procedure that mentions the candidate has a `screenshot`. |

The denominator is these four flags (decision D-R4, 2026-11-06). The earlier five-flag split, with
`has_domain` and `has_situation` as separate checks, is retired and not restored. The
parity test `test_public_order_and_complete_follow_the_four_flag_rule` in
[`apps/api/tests/test_candidate_completeness.py`](../../apps/api/tests/test_candidate_completeness.py)
pins the default order, the `sort_by=completeness` order and `filter[complete]` to this rule.

The full rule, including the manual override of the tag consensus, is section 3 of
[00-architecture.md](../../.plans/candidate-view/00-architecture.md).

## Routes

| Surface | Route | Behavior |
| --- | --- | --- |
| Web | `/documents` | The one document list, served by `GET /api/v1/candidates`: search, sort, category chips, a confidence circle per card, paging. |
| Web | `/candidates` | Redirects to `/documents`. The old filter params are dropped, not translated. |
| Web | `/candidates/:id` | One candidate: canonical category tags and five accordion sections for ingress, egress, flow, evidence and sources. Ingress, egress and flow open by default; evidence and sources start collapsed. Cards on `/documents` link here. |
| API | `GET /api/v1/candidates` | `{items, total, offset, limit}`. Search, sorts and filters are in the browse contract below. |
| API | `GET /api/v1/candidates/{id}` | The detail with `ingress`, `egress`, `sources` and the `screenshot` reference. |
| API | `GET /api/v1/candidates/{id}/screenshot` | The newest screenshot of the candidate's procedures, streamed from the object store. |

None of these routes has a guard. The screenshot route answers:

- 200 with `Cache-Control: public, max-age=31536000, immutable` and an `ETag`.
- 304 when `If-None-Match` carries the current `ETag`.
- 404 when the candidate has no screenshot or does not exist.
- 503 when the R2 read budget is spent.

The machine route `GET /api/v1/discovery/machine/candidates/sources` feeds `capture requeue`. It
needs the machine key. All machine and admin routes are in the single table in
[discovery-layer.md](discovery-layer.md#machine-and-admin-routes-added-by-the-crawl-layer). The
admin tables are in [admin-tables.md](admin-tables.md).

## Browse contract of `GET /api/v1/candidates`

The list-query parser is the shared one (`apps/api/app/shared/list_query/`). An unknown filter or an
invalid value answers 422 and names each bad parameter.

| Parameter | Behavior |
| --- | --- |
| `q` | Case-insensitive title search over all locales. No index. |
| `sort_by` | `confidence`, `completeness`, `mentions`, `title`, `created_at`. |
| `sort_order` | `asc` or `desc`. Needs `sort_by`; alone it answers 422. |
| `filter[category]` | CSV of canonical category codes (`a,b,c`), at most 20 codes. A candidate matches when it carries **any** of them, with **any** score; roots include active descendants. |
| `filter[complete]` | `yes` or `no`, the four completeness flags. Kept for the API; the web list does not expose it. |
| `offset`, `limit` | Paging; `limit` 1 to 100. |

- Category codes combine with OR. More than 20 codes, a code longer than 64 characters, or an unknown
  taxonomy code answers 422 (per code).
- Without `sort_by` the order is confidence descending, then completeness descending, then mentions
  descending, then a deterministic tie-break. With `sort_by` the key is applied and the same
  tie-break follows.
- **There is no 0.05 floor on this path.** A chip matches by the presence of a code, whatever its score.
  `MIN_SUGGESTED_SCORE` (0.05) still applies to the dormant emit payload and to the completeness flags
  `has_category` (open seam S2): a candidate whose only tag scores below it shows a
  tag but no `has_*` flag.
- `confidence` is a float in `[0, 1]` on every tag (`CandidateTag`) and on every card
  (`CandidateCard`). The card value is the maximum tag score among the selected category
  codes, or among all of its tags when no chip is selected. The sort uses the same SQL expression, so
  the number on a card never disagrees with the order.
- A card's `categories` list every canonical code with a score, most confident first.
- The score is computed from the mentions on every request (grouped `best_scores` relation, three
  times per list request; seam S3 in [gaps-and-decisions.md](../../.plans/document-browse-confidence/gaps-and-decisions.md)).
  It mirrors the Python scorer: a manual mention replaces the consensus for its category at `1.0`;
  otherwise the LLM evidence curve and any direct-source confidence combine by noisy-OR.
- The web bands the number: below 0.4 red, 0.4 up to 0.7 yellow, from 0.7 green
  (`apps/web/src/features/documents/utils/confidenceBand.ts`).

## Deploy order

1. Deploy the API first. The candidate view itself had no migration. The document-browse-confidence
   release carries one data migration that deletes the four seeded sample documents by id (see
   [deployment-checklist.md](deployment-checklist.md)).
2. Deploy the web second.

The public pages need both. The web alone shows a failed list. The API alone has no page. After
the API deploy, `GET /api/v1/candidates?limit=1` answers 200 without a key, and the machine
sources route answers 200 with the machine key.

## Screenshot cadence

Production had no screenshot on 2026-10-30. `llm_extract` queues a `capture_screenshot` task after
it posts mentions, but no default drain handles that kind. Drain it on a laptop, within one UTC
day's 570 browser seconds. Cloudflare allows one request every 10 seconds and the worker waits 11,
so about 55 to 65 pages fit in 900 seconds.

```bash
python -m discovery_ingest capture requeue --limit 60 --dry-run
python -m discovery_ingest capture requeue --limit 60
python -m discovery_ingest worker drain --kinds capture_screenshot \
  --max-tasks 5 --max-batches 20 --time-budget-seconds 900 --browser-budget-seconds 570
```

Repeat on the next UTC day until `GET /machine/candidates/sources?missing=screenshot&limit=1`
reports no page. Full steps: [02-live-runs.md](../../.plans/candidate-view/02-live-runs.md) (LR1)
and [discovery-online.md](discovery-online.md).

Recorded result of the first drain (2026-10-30, run
`d3e046e5-bf97-41a7-92dd-546f4db958b5`, `--max-tasks 5 --max-batches 4`):

| Measure | Value |
| --- | --- |
| Tasks claimed, completed, failed | 17, 16, 1 |
| Screenshots before, after | 0, 16 |
| Browser seconds | 43.6 in the drain report; 67.1 of 570 in the budget ledger for that day |
| Artifact bytes used | 6,051,076 before, 18,018,387 after |
| Bytes per screenshot | about 0.75 MB |
| Failed page | one `bundesarchiv.de` page failed before the browser; it is retried later |

A screenshot is a full-page JPEG, 1280 px wide. It weighs about 0.75 MB, more than the 60 to 300 KB
the runbook first assumed. The 9.5 GB artifact cap still holds about 12,000 screenshots. Two
captures were viewed: both show the procedure page. The `arbeitsagentur.de` pages carry a
cookie-consent dialog over the header. The content below it is legible.

## Showcase candidates

Five of the highest-ranking candidates were completed by hand on 2026-10-30, so the pages can be
checked against fully populated data. All five are complete in production (four of four flags).
Four rehabilitation procedures share one page of the Bundesagentur für Arbeit, so one page backs
several candidates.

| Candidate | Role | Categories | Manual edges | Path |
| --- | --- | --- | --- | --- |
| Antrag auf Leistungen zur Teilhabe | ingress only (4 ingress) | work-and-employment, illness-and-care | 2 | `/candidates/2cabe381-6b75-49b1-ae31-c5e1668fe024` |
| Nachweis über den Grad der Behinderung (GdB) | ingress and egress (1 and 2) | health-and-care, work-and-employment, illness-and-care | 1 | `/candidates/ee051d87-5cac-4884-8469-cd274d61a267` |
| Bescheide eines anderen Rehabilitations- oder Sozialversicherungs-Trägers | long title (73 characters), egress only (3) | social-benefits, work-and-employment, illness-and-care | 1 | `/candidates/2bea6edf-0e21-407b-87d9-8db3c2dcaa76` |
| Bestätigung der Ferienbeschäftigung | four categories, 3 ingress | work-and-employment, residence-and-migration, new-job, immigration | 2 | `/candidates/443381cd-85d8-425c-bb45-e0d8560c2f8d` |
| Vollmacht des Betriebes | egress only, untagged before | law-and-justice, new-job | 1 | `/candidates/603cdee2-aeeb-4b7f-9e4b-cc1187d26134` |

The 12-neighbour cap of the diagram is not exercised by real data: the largest side has 4. Unit
tests cover the cap.

The curation file is
[`docs/operations/candidate-curation/showcase.json`](candidate-curation/showcase.json). It was
applied with `candidates curate`, which printed:

```text
mentions_created=5 mentions_updated=0 edges_created=4 edges_updated=3 edges_skipped=0 unknown_codes=0 dry_run=false
```

Three of the edges already existed from extraction and were updated to `manual`.

What `manual` means:

- A mention with `extractor = 'manual'` and codes is authoritative for its category.
  It replaces the extracted consensus, and one procedure suffices.
- An edge with `extractor = 'manual'` was written by a curator from a verbatim sentence of the
  page. It is auditable and removable. Nothing is emitted.
- The description of a candidate is the best mention excerpt. Its source can be a procedure title
  that differs from the candidate, for example GdB shows "Prüfung der beruflichen Eignung von
  Menschen mit Behinderungen beantragen". This is by design.

To undo the curation, run this as the database owner. Count first, then delete in this order:

```sql
SELECT count(*) FROM discovery_candidate_edge WHERE extractor = 'manual';
DELETE FROM discovery_candidate_edge WHERE extractor = 'manual';

SELECT count(*) FROM discovery_candidate_mention WHERE extractor = 'manual';
DELETE FROM discovery_candidate_mention WHERE extractor = 'manual';

SELECT count(*) FROM discovery_document_candidate c WHERE c.status = 'staged'
  AND NOT EXISTS (SELECT 1 FROM discovery_candidate_mention m WHERE m.candidate_id = c.id);
DELETE FROM discovery_document_candidate c WHERE c.status = 'staged'
  AND NOT EXISTS (SELECT 1 FROM discovery_candidate_mention m WHERE m.candidate_id = c.id);
```

The command, its checks and the file schema are in the
[ingest README](../../apps/discovery-ingest/README.md#curate-candidates-by-hand).

## Exposure and the open curation seam

The candidates are unreviewed model output. The 2026-10-30 drain judged 10 to 17 of 58 names to be
false positives, for example `Bescheid`, `Kontaktformular` and annex names. The owner chose to
show them all (decision D1 in [gaps-and-decisions.md](../../.plans/candidate-view/gaps-and-decisions.md)).

- The public item page does not expose staging/completeness internals: there is no "staged and
  unreviewed" banner or completeness checklist. The `/documents` list and detail page retain the
  confidence circle and canonical category links.
- Ranking by confidence, then completeness, pushes sparse and weakly tagged candidates down. Chips
  match by presence, so a weak candidate still appears under a chip; its red circle says so.
- The open seam is a curation gate or a hide list. A hide list is the first follow-up. Until it
  exists, the only way to remove a false positive from the view is a database change.

## Release smoke checks

A person with a browser performs these checks against the deployed stack. The automated suites
cannot judge layout, colour or visible focus. Automated implementation agents had no browser, so
none of these checks is done. Change a status line to the date, the person and the result when
you tick a box.

- [ ] **Showcase candidates.** The five candidates named above are on `/documents` (search each
      title if the default order has pushed it down). Each card shows tags and a confidence circle
      and opens `/candidates/:id` with canonical category tags, ingress and egress cards as designed, the
      diagram and a screenshot. The roles are covered: both-sided, ingress-only, egress-only, a
      long title (tooltip), and many neighbours or the cap note (only unit tests cover this one).  
      Status: not yet performed.
- [ ] **List.** `/documents` lists candidates, the most confident first. Each card shows a
      confidence circle in the band colour (red below 40 %, yellow up to 70 %, green from 70 %)
      with the percentage. Search (submit-applied), the sort (confidence, title, newest, each
      ascending or descending), the category chips and paging work.
      Every change returns to page one, and a reload or a shared URL restores the same view. A
      root chip is solid swiss red, a subcategory chip uses a lighter red. The empty and
      error states are readable. `/candidates` redirects to `/documents`.  
      Status: not yet performed.
- [ ] **Detail.** `/candidates/:id` shows the title, the description with its source attribution,
      canonical category links, and five accordion sections: ingress, egress, flow, evidence and
      sources. The first three are expanded by default; evidence and sources start collapsed.
      A candidate without edges shows the "no dependencies staged" note. A reload of the
      screenshot answers 304.
      Status: not yet performed.
- [ ] **Light, dark and narrow.** Check light mode, dark mode and a narrow layout (below `md`).
      The flow accordion remains present below `md`; its diagram may use a responsive fallback, but
      the section is not removed. Focus rings, link names and the text alternative of the diagram
      are present.
      Status: not yet performed.
- [ ] **Menu.** The menu has no Candidates and no Suggest link. Home is centred. The menu closes
      after Home, a Documents link, the language flag or Sign out, and stays open when the colour
      mode is switched.  
      Status: not yet performed.
- [ ] **Admin documents table.** On `/admin/discovery/documents` the toolbar is in the table
      header, every column sorts, filters appear as removable chips and the Ready quick filter
      works. A long title is clipped, and its tooltip shows the whole text on hover and on
      keyboard focus.  
      Status: not yet performed.
- [ ] **Admin catalogue and coverage.** `/admin/discovery/catalogue` and
      `/admin/discovery/coverage` show different top blocks. The catalogue chips filter the
      table. Coverage is unchanged.  
      Status: not yet performed.

## Candidate view polish smoke checks

Added once the `candidate-view-polish` suite's five chapters landed on
`feat/plans-candidate-view-polish`; plan and decisions:
[`.plans/candidate-view-polish/`](../../.plans/candidate-view-polish/00-architecture.md). As with
the checks above, a person with a browser performs these; no automated implementation agent in
this suite had one.

- [ ] **Body panel boundary.** `/candidates/:id` shows a visible `surface`/`border`/shadow panel
      around the page body, distinct from the `bg.canvas` page background behind it. The same
      boundary appears on `/documents`, and at least one admin page (for example
      `/admin/discovery/catalogue`), in both light and dark mode. No page looks broken or
      edge-to-edge-clipped by the new panel, including a wide table page.  
      Status: not yet performed.
- [ ] **Scrollable, unbannered screenshot.** On a candidate detail page backed by a source known
      to show a cookie-consent banner, the evidence screenshot shows no banner across the top, and
      the full captured page is reachable by scrolling vertically inside the screenshot frame
      (not cropped to the first viewport).  
      Status: not yet performed.
- [ ] **Plain-language ingress/egress headings.** On `/candidates/:id`, the two neighbour section
      headings read "Documents you need first" and "Documents that need this one" (German:
      "Dokumente, die du zuerst brauchst" / "Dokumente, die dieses benötigen"), not "Ingress" /
      "Egress", and there is no separate subtitle line repeating the same text underneath.  
      Status: not yet performed.
- [ ] **Collapsed sources accordion.** On `/candidates/:id`, the Sources section is collapsed by
      default on first load and expands to show the procedure list (title, portal link, role
      badge, excerpt) on click.  
      Status: not yet performed.
