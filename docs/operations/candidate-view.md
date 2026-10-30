# Candidate view: operator guide and release smoke checks

The public candidate view lists the staged document candidates of the extraction suite and opens
each one with its dependencies, a flow diagram and a screenshot of the source page. This guide
covers the routes, the deploy order, the screenshot cadence, the hand-completed showcase
candidates, the exposure risk and the release smoke checks. Plan and decisions:
[`.plans/candidate-view/`](../../.plans/candidate-view/00-architecture.md).

## What it is

The view is public, read-only and unreviewed. Anyone can open it without a login. It shows every
staged or emitted candidate, ranked by completeness. It never emits, votes, moderates or edits.

Completeness is five yes-or-no flags per candidate. A candidate is `complete` when all five are
true. The list sorts by the count, highest first.

| Flag | True when |
| --- | --- |
| `has_domain` | At least one accepted domain code (the tag consensus, or a `manual` code). |
| `has_situation` | At least one accepted life-situation code (same rule). |
| `has_edges` | At least one staged edge has the candidate as parent or as required end. |
| `has_snapshot` | A procedure that mentions the candidate has an `html_snapshot`. |
| `has_screenshot` | A procedure that mentions the candidate has a `screenshot`. |

The full rule, including the manual override of the tag consensus, is section 3 of
[00-architecture.md](../../.plans/candidate-view/00-architecture.md).

## Routes

| Surface | Route | Behavior |
| --- | --- | --- |
| Web | `/candidates` | The ranked list: search, domain and situation chips, a "complete only" switch, paging. |
| Web | `/candidates/:id` | One candidate: tags, ingress and egress cards, the flow diagram, the screenshot, the sources. |
| API | `GET /api/v1/candidates` | `{items, total, offset, limit}`. Sort `completeness` (default), `title`, `mentions`, `created_at`. Filters `complete`, `domain`, `situation`; search `q`. |
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

## Deploy order

1. Deploy the API first. The release has no migration.
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
checked against fully populated data. All five are complete in production (five of five flags).
Four rehabilitation procedures share one page of the Bundesagentur für Arbeit, so one page backs
several candidates.

| Candidate | Role | Domain | Situation | Manual edges | Path |
| --- | --- | --- | --- | --- | --- |
| Antrag auf Leistungen zur Teilhabe | ingress only (4 ingress) | work-employment | illness-care | 2 | `/candidates/2cabe381-6b75-49b1-ae31-c5e1668fe024` |
| Nachweis über den Grad der Behinderung (GdB) | ingress and egress (1 and 2) | health-insurance, work-employment | illness-care | 1 | `/candidates/ee051d87-5cac-4884-8469-cd274d61a267` |
| Bescheide eines anderen Rehabilitations- oder Sozialversicherungs-Trägers | long title (73 characters), egress only (3) | social-benefits, work-employment | illness-care | 1 | `/candidates/2bea6edf-0e21-407b-87d9-8db3c2dcaa76` |
| Bestätigung der Ferienbeschäftigung | two codes on both axes, 3 ingress | work-employment, residence-migration | new-job, immigration | 2 | `/candidates/443381cd-85d8-425c-bb45-e0d8560c2f8d` |
| Vollmacht des Betriebes | egress only, untagged before | law-justice | new-job | 1 | `/candidates/603cdee2-aeeb-4b7f-9e4b-cc1187d26134` |

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

- A mention with `extractor = 'manual'` and codes is authoritative for its axis (domain or life
  situation). It replaces the extracted consensus, and one procedure suffices.
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

- Every public page carries a "staged, unreviewed" banner (D16).
- Ranking by completeness pushes sparse candidates down.
- The open seam is a curation gate or a hide list. A hide list is the first follow-up. Until it
  exists, the only way to remove a false positive from the view is a database change.

## Release smoke checks

A person with a browser performs these checks against the deployed stack. The automated suites
cannot judge layout, colour or visible focus. Automated implementation agents had no browser, so
none of these checks is done. Change a status line to the date, the person and the result when
you tick a box.

- [ ] **Showcase candidates.** The five candidates named above are at the top of `/candidates`,
      each with five present chips. Each opens with tags on both axes, ingress and egress cards as
      designed, the diagram and a screenshot. The roles are covered: both-sided, ingress-only,
      egress-only, a long title (tooltip), and many neighbours or the cap note (only unit tests
      cover this one).  
      Status: not yet performed.
- [ ] **List.** `/candidates` lists candidates with complete ones first. Each card shows its
      completeness chips. The "complete only" switch, the search, the domain and situation chips
      and paging work, and each filter change returns to page one. The empty and error states are
      readable.  
      Status: not yet performed.
- [ ] **Detail.** `/candidates/:id` shows the title, the description with its source attribution,
      the ingress and egress cards, the flow diagram (arrows converge on the title card and
      diverge to the egress cards), the screenshot and the sources. A candidate without edges
      shows the "no dependencies staged" note. A reload of the screenshot answers 304.  
      Status: not yet performed.
- [ ] **Light, dark and narrow.** Check light mode, dark mode and a narrow layout (below `md`).
      The diagram is hidden below `md` and the card lists remain. Focus rings, link names and the
      text alternative of the diagram are present.  
      Status: not yet performed.
- [ ] **Menu.** The menu has a Candidates icon link for everyone, not only for admins.  
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
