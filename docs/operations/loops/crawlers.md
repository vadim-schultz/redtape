# Crawlers (chief of staff)

This suite is orchestrated as a **chief of staff** plan.

Plan suite folder: `.plans/crawlers/` (architecture, rollout, decisions, chapters, ledger).

**Loop branch:** `feat/crawlers`
**Release branch:** `main`

## How to run

1. Launch **chief of staff** with plan folder `.plans/crawlers/`.
2. Run one chapter-implementer per chapter, in the order of
   [`01-rollout.md`](../../../.plans/crawlers/01-rollout.md): ingest CI, fetcher hardening, kind-filtered
   claim, retry, drain throughput, candidate model, PVOG harvester, admin queue kinds, menu icon row, admin
   Documents list, candidate emit, FIM key fix, object store, artifact API, free-tier guards (chapter 23, executed
   between 14 and 15), Cloudflare render and snapshot, admin Artifacts panel, extractor framework, first extractor
   (chapter 18, optional), Cloudflare screenshot capture, admin document detail, docs sync, operator steps.
3. Each chapter PR targets the loop branch only. The PR's GitHub Actions checks are the authoritative gate
   (`gh pr checks --watch`). When the shared Actions quota is exhausted, remote CI fails in seconds with no steps; the
   chapter then merges on the local gate (ruff, mypy, the full test run) and says so in its PR and in the ledger.
4. Chapters with a live gate dispatch the named workflow with `gh workflow run` and record the run ID in
   [`run-ledger.md`](../../../.plans/crawlers/run-ledger.md). A missing live gate (for example storage not yet
   provisioned) never blocks a merge; record it as deferred with the operator step it needs.
5. When the ledger is complete, open the release PR from the loop branch to `main`.

## Operator dependencies

Manual steps are listed in order in
[`chapters/22-operator-manual-steps.md`](../../../.plans/crawlers/chapters/22-operator-manual-steps.md).
The ones that gate live verification are the census queries (S12), the fetch repair (S11), the R2 bucket,
access key, Render variables and GitHub probe secrets (S1–S4), the Cloudflare browser token, its GitHub
secrets and the browser probe (S15–S17), Cloudflare billing notifications and the ledger caps (S19, S21), and the
schedule variables (S13). The operator ticks them in
[`docs/operations/crawlers-operator-checklist.md`](../crawlers-operator-checklist.md). Ask for them early; do not wait
for the last chapter. `gh workflow run` answers 404 for a workflow file that is not on `main`, so several live gates
run only after the release.

## Rules for implementers

- Workers never use `DATABASE_URL`. Storage credentials never reach GitHub Actions except the probe
  workflow.
- The Cloudflare browser token (`Browser Run - Edit` only) lives in GitHub Actions secrets and the
  operator's local environment, never in Render or the web app. Browser kinds (`render_page`,
  `capture_screenshot`) are never in a default kind list and are drained only with both budgets (run time and
  browser seconds). A Cloudflare quota or an unavailable object store releases tasks (no attempt consumed);
  it never fails them.
- Scheduled jobs never emit. Candidate emit is a deliberate operator action.
- A catalogue service is a procedure, not a document.
- Every drain is bounded and reports why it stopped.
- New navigation links are `react-icons` buttons in the single `HStack` row of the Documents menu, added to
  the config array; never a new row or a text link.
- Every chapter ends with paired happy and negative tests and a recorded refactor outcome.

## What the suite delivers

Built on `feat/crawlers`; the release PR to `main` is pending, so none of it runs in production yet.

| Area | Delivered (chapters) |
| --- | --- |
| Queue | Kind-filtered claim, safe legacy default (3); retry with backoff, release route (4, 14); multi-batch bounded drain, queue summary and `remaining` (5); hardened polite fetcher with redirects, robots.txt and address guard (2) |
| Documents | Candidates and mentions with provenance (6); PVOG payload harvest (7); admin Documents list and detail (10, 20); manual candidate emit CLI and routes, `official_url` optional on `new_document` (11) |
| Enrichment | FIM steckbrief key fix and `fim probe` (12) |
| Storage | Object-store port with an R2 adapter (S3 API, Cloudflare R2) (13); artifact model, upload, read and status routes, byte cap (14); admin Artifacts panel (16) |
| Free-tier guards | Budget ledger, metered store, database soft limit, Actions minutes (23) |
| Browser | Cloudflare render and `render_page`, `discovery-render.yml`, browser probe (15); extractor framework and `extract_page` (17); `capture_screenshot` (19) |
| Admin | Task kinds, attempts, retry time and result note on the Tasks screen, candidate and artifact counts on Coverage (8, 16); one-row menu with a Documents icon (9) |
| Docs and ops | Runbooks, this loop document and the operator checklist (21, 22); ingest CI (1) |

Not built: Chapter 18 (first page extractor, optional; hand-written extractors wait for the
[extraction](../../../.plans/extraction/01-rollout.md) suite). No extractor is registered, so every `extract_page` task
completes with `no_extractor` and no `capture_screenshot` task is queued yet. Document candidates come from the PVOG
payload harvest only.

## Known gaps

Each is also in the ledger or in
[`gaps-and-decisions.md`](../../../.plans/crawlers/gaps-and-decisions.md). Nothing here is a reason to hold the release.

- **Live gates are open.** Every chapter merged with tests against fakes. The live gates need the release on `main` and
  the operator steps; remote CI did not run for chapters 6 to 21 because the Actions quota was exhausted. The release
  PR is the first remote run of that code.
- **FIM enrichment has a label but no `metadata` claim.** The enrich helpers label entities from `title` (falling back
  to `titel`, then `leistungsbezeichnung`). The real steckbrief has no `kurztext`, so no `metadata` claim is written;
  that is how the data is, not a defect. Stammtext references are not fetched.
- **Inherited rollback gap.** `SuggestionService._insert` rolls back the whole session on an `IntegrityError`, which
  could undo earlier uncommitted updates in one emit batch. Only a concurrent same-key race triggers it.
- **Byte cap counts rows.** `OBJECT_STORE_MAX_BYTES` sums `discovery_artifact.byte_size`, not objects. An orphaned
  object (a failed insert after the put, or a pruned snapshot whose delete failed) is not counted. The 2 GiB margin
  below R2's 10 GB absorbs it. Two concurrent identical uploads race on the unique key (one answers 500).
- **Browser probe is partial.** Not probed: the body of the daily-limit 429, a real login page, the pixel size of a
  full-page JPEG. Diff a plain fimportal body against its rendered DOM before the roughly 22-run backlog starts.
- **Counting is approximate.** The R2 meter shares the request session, so a reservation can roll back with a failed
  request, and S3 retries can exceed the counted operations. The 20 percent margin covers it. The `neurons`
  resource exists but nothing reserves it yet.
- **Candidate race.** Two concurrent batches that create the same new candidate could answer 500 on the unique
  constraint. One drain worker at a time avoids it.
- **Fetcher.** A DNS-rebinding race in the address guard, and `httpx.InvalidURL` is not caught.
- **Harvest.** PVOG module `14` text lists are not harvested (links only). Bump `PVOG_HARVESTER_VERSION` in the API
  `fanout.py` together with `EXTRACTOR_VERSION` in `harvest/pvog.py`.
- **Web.** The admin fetches artifacts with `limit=50` and has no paging, so evidence beyond 50 items is cut off. The
  menu panel is content-sized and extends past a 360 px viewport. The "Pending review" chip on a document is an
  assumption: the API cannot tell whether the suggestion was reviewed since.
- **German strings.** The German copy of chapters 8, 10, 16 and 20 was machine-written and needs native review. The key
  list is in the operator checklist.
- **Admin `kind` filter.** The query parameter is typed to the enum, so the API must change when the enum gains a value.
- **Code size.** `cli.py`, `api_client.py` and older drain code remain over 100 lines; older `httpx.Client` blocks in
  the API client are a follow-up to fold into `_call`.
- **Another suite's status.** `.plans/README.md` and parts of the voting-moderation rollout still say "planned" while
  the API implements votes, tally, transitions and both promote handlers. This suite does not edit another suite's status.

## Out of scope (named future suites)

- Link-following frontier crawling and crawl budgets.
- Freshness crawling of existing documents.
- LLM extraction.
- Resolving mentions to canonical documents and emitting `new_requirement` suggestions.
- A web voting and moderation UI.
- Attaching artifacts to suggestions as `evidence` rows.
