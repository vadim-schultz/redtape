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
   Documents list, candidate emit, FIM key fix, object store, artifact API, Cloudflare render and snapshot,
   admin Artifacts panel, extractor framework, first extractor, Cloudflare screenshot capture, admin document
   detail, docs sync, operator steps.
3. Each chapter PR targets the loop branch only. Local checks are best-effort; the PR's GitHub Actions
   checks are the authoritative gate (`gh pr checks --watch`).
4. Chapters with a live gate dispatch the named workflow with `gh workflow run` and record the run ID in
   [`run-ledger.md`](../../../.plans/crawlers/run-ledger.md). A missing live gate (for example storage not yet
   provisioned) never blocks a merge; record it as deferred with the operator step it needs.
5. When the ledger is complete, open the release PR from the loop branch to `main`.

## Operator dependencies

Manual steps are listed in order in
[`chapters/22-operator-manual-steps.md`](../../../.plans/crawlers/chapters/22-operator-manual-steps.md).
The ones that gate live verification are the census queries (S12), the fetch repair (S11), the Supabase
bucket, access key, Render variables and GitHub probe secrets (S1–S4), the Cloudflare browser token, its GitHub
secrets and the browser probe (S15–S17), and the schedule variables (S13). Ask the operator for them early;
do not wait for the last chapter.

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

To be filled in by chapter 21 when the suite ships: kind-filtered claim and retry, multi-batch drain with a
known `remaining`, document candidates with provenance and an admin Documents screen, PVOG payload harvest,
manual candidate emit, FIM enrichment that fires, an object-store port with a Supabase adapter, rendered
snapshot and screenshot artifacts (Cloudflare Browser Run, free plan) visible in the admin, an extractor
framework and the first page extractor.

## Known gaps

To be filled in by chapter 21 from the ledger.

## Out of scope (named future suites)

- Link-following frontier crawling and crawl budgets.
- Freshness crawling of existing documents.
- LLM extraction.
- Resolving mentions to canonical documents and emitting `new_requirement` suggestions.
- A web voting and moderation UI.
- Attaching artifacts to suggestions as `evidence` rows.
