# Crawlers — Run ledger

**Loop branch:** `feat/crawlers`
**Release branch:** `main`
**Release PR:** staged release of chapters 1–6 to `main`: [PR #191](https://github.com/vadim-schultz/redtape/pull/191). The final release (a second PR `feat/crawlers` → `main`) is still pending.

Update this ledger after every chapter implementation or documented operator verification. A chapter is not complete until its gate, its live gate (or the reason it is deferred), and its refactor outcome are recorded. Record GitHub Actions run IDs for every live gate.

| Chapter | Plan | Status | Verification | Refactor outcome | Live gate (run ID) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [Ingest CI](chapters/01-ingest-ci.md) | merged | [PR #184](https://github.com/vadim-schultz/redtape/pull/184) into `feat/crawlers`; `lint-and-test` green (51 passed); path-filter negative confirmed (throwaway PR #185 closed) | audited, nothing needed (one job, ~30 s) | n/a (no live gate); Loop A 39942708773, Loop B red 39942856076 (format) / 39942946857 (assertion), green after revert 39943054982 | Required check name if branch protection is added: `lint-and-test`. Local full `ci.sh` not run (no Docker/PyPI); ingest section run by hand. |
| 2 | [Fetcher hardening](chapters/02-fetcher-hardening.md) | merged | [PR #186](https://github.com/vadim-schultz/redtape/pull/186) into `feat/crawlers`; `lint-and-test` green (run 39944869596), 126 passed locally | extracted `next_url`, `validate_destination`, `RobotsCache`, `read_reply`, `HostPacer`, `classified`; shared `FetchOutcome.failed`; `fetcher.py` 115 lines (extract `_request`/`_stream` if it grows in ch. 15) | **deferred**: `gh workflow run discovery-drain.yml --ref feat/crawlers` returned HTTP 404 — `workflow_dispatch` workflows only register once the file is on `main`. Also needs ch. 22 step S11 (re-pend 3xx tasks). | Live gates of ch. 5, 7, 15, 18 that dispatch `discovery-drain.yml` share this limit; they run after the release merge. Edited two existing drain tests (monotonic ticks; extra per-host interval for robots.txt, suite ~24 s). Known limit: DNS-rebinding race in address guard. `httpx.InvalidURL` still uncaught. Ch. 4 handoff: `retryable`/`failure` on `FetchOutcome` are not yet sent to the API. |
| 3 | [Kind-filtered claim and enum groundwork](chapters/03-kind-filtered-claim.md) | merged | [PR #187](https://github.com/vadim-schultz/redtape/pull/187) into `feat/crawlers`; API `lint-and-test`, `migrations` and ingest `lint-and-test` green (run 39946230886 / 39946230715); local API 584 passed, ingest 133 passed, `check_migrations.sh` passed against local Postgres | `LEGACY_TASK_KINDS` single constant; `EnqueueOutcome` dataclass; `_enqueue_target` helper; measure_code_rules clean | **deferred**: `discovery-drain.yml` not on `main` (dispatch would 404). Still to run after release: default dispatch, and `kinds=capture_screenshot` must stop with `queue_empty`. | Migration `20261024_task_kinds` (down `20261023_discovery_run`); labels preserved on downgrade. Migration chapters (4, 6, 14) must update the hard-coded head in `tests/test_discovery_staging_migration_retry.py` and `tests/test_check_migrations_script.py`. `list_pending_tasks_for_claim` now requires `kinds`; worker `--kinds` validated up front. Ch. 4 must mark the unknown-kind path non-retryable. Web kind union left to ch. 8. |
| 4 | [Retry and backoff](chapters/04-retry-and-backoff.md) | merged | [PR #188](https://github.com/vadim-schultz/redtape/pull/188) into `feat/crawlers`; API `lint-and-test`, `migrations`, ingest `lint-and-test` green; local API 595 passed, ingest 138 passed, `check_migrations.sh` passed | `task_retry.py` (policy), `repository/task_clauses.py` (`claimable(now)`, reused by ch. 5), `worker/settle.py`; `handle_enrich_metadata` guards left (pre-existing length) | **deferred**: `discovery-drain.yml` not on `main`; needs ch. 22 S11 re-pend of 2 transport-failed tasks first | Migration `20261025_task_retry` (head). `fail(task_id, error, *, retryable=False, now)`; `reclaim_expired_claims` / `list_pending_tasks_for_claim` take `now`. Two HTTP fail-route tests were written after green (regression guards, never red). Only fetch outcomes carry `retryable`; all other worker failures are non-retryable incl. unknown kind. Admin does not yet show `attempt_count`/`not_before` (ch. 8). Pre-existing `mypy .` test-file errors in ingest (CI runs `mypy discovery_ingest` only). |
| 5 | [Drain throughput and queue summary](chapters/05-drain-throughput-and-queue-summary.md) | merged | [PR #189](https://github.com/vadim-schultz/redtape/pull/189) into `feat/crawlers`; API `lint-and-test`, `migrations`, ingest `lint-and-test` green; local API 603 passed, ingest 141 passed | `claimable`/`delayed`/`expired_lease` in one module; `resolve_task_kinds` shared; `_report`/`_remaining` in drain; `drain.py` now >100 lines (split candidate in ch. 15) | **deferred**: `discovery-drain.yml` not on `main`. After release: dispatch `max_batches=3 time_budget_seconds=600` (expect `batches=3`, numeric `remaining`); two dispatches show `remaining` falling; concurrency group serialises; schedule stays off while `DISCOVERY_DRAIN_SCHEDULE` unset. | `GET /machine/tasks/summary` (repeated `?kinds=`). Daily schedule `0 4 * * *` ships switched off (variable gate; `schedule:` only fires from `main` anyway). Empty `time_budget_seconds` now falls back to 1500. GitHub keeps one pending run per concurrency group, so a third queued drain cancels the older pending one. Maintenance concurrency is job-level. `docs/operations/scheduled-jobs.md` left to ch. 21. |
| 6 | [Candidate staging model and API](chapters/06-candidate-staging-model-and-api.md) | merged (no remote CI) | [PR #190](https://github.com/vadim-schultz/redtape/pull/190) merged into `feat/crawlers` on 2026-10-23 without remote CI. Local: ruff/mypy clean, 638 passed (`REQUIRE_DB=1`, throwaway Postgres), `check_migrations.sh` passed. Remote `lint-and-test` / `migrations` (run 39950676123) failed in 3 s with no steps because of Actions billing (shared account quota exhausted), not because of the code. | Loop B shared timestamp mixins; C split `_upsert_mention`/`_find_mention`; D extracted `_with_mention_counts()` | n/a (no live gate; after deploy `GET /admin/candidates` should return an empty list) | Migration `20261026_candidates` (down `20261025_task_retry`). Atomic batch rejection; 422 for blank/punctuation-only title or >100 items, 404 for unknown catalogue row. Known gap: two concurrent batches creating the same new candidate could 500 on the unique constraint (acceptable for a single drain worker). **Remote CI still owed**: the chapter 7 PR doubles as the first remote verification of this code. |
| 7 | [PVOG payload harvester](chapters/07-pvog-payload-harvester.md) | planned | | | | |
| 8 | [Admin queue kinds and metrics](chapters/08-admin-queue-kinds-and-metrics.md) | planned | | | | |
| 9 | [Menu icon row](chapters/09-menu-icon-row.md) | planned | | | | |
| 10 | [Admin Documents list](chapters/10-admin-documents-list.md) | planned | | | | |
| 11 | [Candidate emit](chapters/11-candidate-emit.md) | planned | | | | |
| 12 | [FIM key fix](chapters/12-fim-key-fix.md) | planned | | | | |
| 13 | [Object store port and Supabase adapter](chapters/13-object-store-port-and-supabase-adapter.md) | planned | | | | |
| 14 | [Artifact model and API (with browser-task groundwork)](chapters/14-artifact-model-and-api.md) | planned | | | | |
| 15 | [Cloudflare render and snapshot](chapters/15-cloudflare-render-and-snapshot.md) | planned | | | | |
| 16 | [Admin Artifacts panel (and render_page kind)](chapters/16-admin-artifacts-panel.md) | planned | | | | |
| 17 | [Extractor framework and extract_page](chapters/17-extractor-framework.md) | planned | | | | |
| 18 | [First page extractor](chapters/18-first-page-extractor.md) | planned | | | | |
| 19 | [Screenshot capture](chapters/19-screenshot-capture.md) | planned | | | | |
| 20 | [Admin document detail and evidence](chapters/20-admin-document-detail-and-evidence.md) | planned | | | | |
| 21 | [Docs sync](chapters/21-docs-sync.md) | planned | | | | |
| 22 | [Operator manual steps](chapters/22-operator-manual-steps.md) | planned | | | | |

## Release checklist

- [ ] The ingest package has its own CI workflow and it is green (chapter 1).
- [ ] Redirects are followed and no longer recorded as success (chapter 2).
- [ ] The scheduled drain claims only kinds it handles, retries transient failures, and drains more than one batch with a known `remaining` (chapters 3–5).
- [ ] Document candidates exist with mentions and provenance, and the admin Documents screens show them (chapters 6, 7, 10).
- [ ] The navigation icons render in one unbroken row (chapter 9).
- [ ] One operator-driven candidate emit created pending `new_document` suggestions (chapter 11).
- [ ] FIM enrichment fires for GovData rows and produces claims (chapter 12).
- [ ] Object-store probe is green and rendered snapshots appear as artifacts (chapters 13–16).
- [ ] The Cloudflare browser probe is recorded and a render run on the free plan ended inside its budgets, with tasks released rather than failed on any limit (chapter 15).
- [ ] At least one extractor produced candidates from live snapshots (chapters 17–18).
- [ ] A screenshot was captured through Cloudflare and is visible in the admin (chapters 19–20).
- [ ] Operations docs and the loop doc are synchronized; evidence-storage and discovery-layer pointers are updated (chapter 21).
- [ ] The operator checklist is complete (chapter 22).
- [ ] Link/frontier crawling, freshness, LLM extraction, requirement emit, and a web voting UI remain out of scope.
- [ ] Release PR from `feat/crawlers` to `main` is ready.

## Resume next month (staged release)

Chapters 1–6 reached `main` on 2026-10-23 through a staged release PR, merged without remote CI because the shared GitHub Actions quota (Free plan, 2,000 min across all repos) was exhausted. `feat/crawlers` stays the loop branch. **Next chapter: 7** ([07-pvog-payload-harvester.md](chapters/07-pvog-payload-harvester.md)). The final release is a second PR `feat/crawlers` → `main`.

The Actions budget work was done in the separate suite [`.plans/gha-budget/`](../gha-budget/01-rollout.md) (loop branch `chore/gha-budget`, released to `main` the same day as [PR #199](https://github.com/vadim-schultz/redtape/pull/199); the owner's operator steps O1–O5 are in [docs/operations/gha-budget.md](../../docs/operations/gha-budget.md)). It retires keep-alive, makes platform maintenance monthly, adds the drain budget variable and cancels superseded CI runs.

First actions once the quota resets (about 2026-11-01):

1. Confirm Actions billing works (any workflow job starts instead of failing in 3 s).
2. `feat/crawlers` already contains `main` as of 2026-10-23 (including the gha-budget release, PR #199). Still run `git checkout feat/crawlers && git pull && git merge main` to pick up anything merged since.
3. Chapter 6 never had remote CI. The chapter 7 PR doubles as its remote verification; if it is red because of chapter 6 code, fix that in a fix-up branch before continuing.
4. The deferred live gates of chapters 2, 3, 4 and 5 can run now, because `discovery-drain.yml` is on `main`. Keep them short (`max_batches=3 time_budget_seconds=600`), and run chapter 22 step S11 (re-pend the 3xx tasks) first.
5. Keep the repository variable `DISCOVERY_DRAIN_SCHEDULE` unset until chapter 22 step S13.

Budget guard: this repo's share is roughly 960 min/month (the other repos use the rest). Chapters 7–22 are about 16 PRs at roughly 5–10 billed minutes each (web CI only when `apps/web` changes), so run the local gate before every push and check the usage report before dispatching a live gate. The Cloudflare plan revision removes the Playwright capture workflow, the Chromium install and the `capture-integration` CI job, but chapter 15's render backlog (roughly 18 fifteen-minute runs, about 4.5 hours of runner time for the 1,423 known pages) is a deliberate spend: prefer local runs (operator step S18) and keep `DISCOVERY_RENDER_SCHEDULE` unset until there is budget.

Before chapter 15 starts, the operator does S15–S17 of chapter 22 (Cloudflare token and secrets, browser probe, storage check); chapter 15's Step 0 is the probe.

Launch: `/chief-of-staff` on `.plans/crawlers/`, loop branch `feat/crawlers`, resume.

**Last orchestration:** 2026-10-23 — chapters 1–6 merged into `feat/crawlers` and staged-released to `main` without remote CI (Actions quota exhausted); resume at chapter 7 after the quota resets.

**Plan revision:** 2026-10-23 — chapters 14–22 were re-planned around Cloudflare Browser Run quick actions on the free plan. Chapter 14 gained the `render_page` label, `result_note`, the release route and a storage status route; chapter 15 became the Cloudflare render chapter (probe, throttled client, `render_page`, `discovery-render.yml`); chapter 16 widens the web kind union; chapter 17 lost its API work; chapter 19 lost Playwright, the `[capture]` extra, its workflow and its CI job. Decisions D14 (replaced) and D19–D22 record why. Chapters 1–13 are unaffected.
