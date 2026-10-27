---
name: "Chapter 21 — Docs sync"
overview: "Synchronize operator runbooks, the loop document, ingest README, plan indexes and the neighbouring suites with what this suite shipped, and add documentation contract tests."
todos:
  - id: runbooks
    content: "Update discovery-layer, discovery-online, scheduled-jobs, deployment-checklist and suggestion-api docs"
    status: pending
  - id: loop-doc
    content: "Confirm docs/operations/loops/crawlers.md matches what shipped"
    status: pending
  - id: neighbours
    content: "Amend evidence-storage, discovery-layer ch. 20, discovery-operations D11 and suggestion-interface D9"
    status: pending
  - id: docs-tests
    content: "Add paired documentation contract tests and a link check"
    status: pending
isProject: false
---

# Chapter 21 — Docs sync

**Repo:** `redtape` (`docs/operations`, `.plans`, `apps/discovery-ingest/README.md`, `apps/api/tests`) · **Branch:** `docs/crawlers-docs-sync` · **Status:** planned

**Depends on:** [01](01-ingest-ci.md)–[20](20-admin-document-detail-and-evidence.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Leave the repository describing what exists. This chapter changes documentation and documentation tests only; any code discovered to be wrong is reported in the ledger and fixed in its own chapter.

## Documentation targets

| Document | Update |
| --- | --- |
| [`docs/operations/discovery-layer.md`](../../../docs/operations/discovery-layer.md) | Task kinds and the kind filter, candidates and mentions vocabulary, the document-first flow, the procedure-versus-document rule, manual candidate emit and the CLI |
| [`docs/operations/discovery-online.md`](../../../docs/operations/discovery-online.md) | Bounded multi-batch drain, retry and backoff, `remaining`, failure triage by kind, rendered snapshots, the browser kinds and their budgets (Cloudflare free plan: rate limit, daily browser minutes, release on `429`), the new stop reasons and the storage-unavailable behaviour |
| [`docs/operations/gha-budget.md`](../../../docs/operations/gha-budget.md) | Replace the "about 960 minutes" assumption by the 1,000 minutes a month cap for this repository (GitHub's free 2,000 are shared), the CI reserve, the drain allowance and the monthly comparison of the ledger with GitHub's usage report (chapter 23, operator step S20). October's actual use of 960 stays as history |
| [`docs/operations/scheduled-jobs.md`](../../../docs/operations/scheduled-jobs.md) | The budget ledger and its caps (chapter 23), `discovery-drain.yml`, `discovery-render.yml`, the probe workflows (storage and browser), repository variables that gate schedules (`DISCOVERY_DRAIN_SCHEDULE`, `DISCOVERY_RENDER_SCHEDULE`), the storage secrets used only by the probe, the Cloudflare secrets used by the render workflow and the browser probe, the concurrency group, and that no scheduled job emits |
| [`docs/operations/deployment-checklist.md`](../../../docs/operations/deployment-checklist.md) | Render `OBJECT_STORE_*` variables (R2 endpoint form `https://<account_id>.r2.cloudflarestorage.com`, region `auto`, `OBJECT_STORE_MAX_BYTES`) and the ledger cap variables, optional-at-boot behaviour, 503 on artifact routes when unset and 507 at the byte cap, and that the Cloudflare token is deliberately **not** a Render variable |
| [`docs/operations/suggestion-api.md`](../../../docs/operations/suggestion-api.md) | `official_url` is optional on `new_document` (decision D8) and how conflicts behave without it |
| [`docs/operations/loops/crawlers.md`](../../../docs/operations/loops/crawlers.md) | Chief-of-staff instructions, loop branch, chapter order, release protocol, delivered scope and known gaps |
| [`apps/discovery-ingest/README.md`](../../../apps/discovery-ingest/README.md) | New commands (`worker drain --kinds` with `--browser-budget-seconds`, `candidates emit`, `fim probe`, `browser probe`, `artifacts download`), the `CLOUDFLARE_*` and `BROWSER_*` settings, and running a browser drain locally. No Playwright or browser install is documented because none exists |
| [`apps/api/.env.example`](../../../apps/api/.env.example) (or the root `.env.example`, whichever holds API settings) | `OBJECT_STORE_*` with comments. The Cloudflare variables belong to the worker, not the API, and go in `apps/discovery-ingest`'s example file |
| [`.plans/README.md`](../../README.md) | Replace the crawlers entry (twenty-three chapters, queue-based, status, first chapter) and keep the extraction entry |
| [`docs/planning/STATUS.md`](../../../docs/planning/STATUS.md) | Record the suite when it ships |

## Neighbouring suites to amend

When this suite was planned, short "planned amendment" notes and pointers were already added to the suites below. This chapter rewrites them to the **shipped** state (statuses, final module paths, the chosen checksum variant).

- [evidence-storage](../../evidence-storage/00-architecture.md): decision D1 (R2) is confirmed and made provider-neutral in wording (any S3 service by configuration); chapters 1 and 2 are absorbed by [chapter 13](13-object-store-port-and-r2-adapter.md) (`app/shared/object_store`); a new open seam describes bridging `discovery_artifact` rows to suggestion `evidence` rows at emit time (content-addressed keys make this a copy or a shared key); the remaining chapters keep their meaning.
- [discovery-layer chapter 20](../../discovery-layer/chapters/20-crawler-frontier-adapter.md): mark it superseded by this suite and point to chapters 3, 15, 17 and 19.
- [discovery-operations decision D11](../../discovery-operations/gaps-and-decisions.md): replace "deferred" wording for the crawler with a pointer here.
- [suggestion-interface decision D9](../../suggestion-interface/gaps-and-decisions.md): note that `official_url` is now optional on `new_document` and why.
- Observation for the owner of [voting-moderation](../../voting-moderation/01-rollout.md): the API already implements votes, tally, transitions and both promote handlers, while `.plans/README.md` and parts of that rollout still say "planned". This suite does not edit another suite's status; the ledger notes the mismatch.

## TDD and documentation gate

**Red** (`apps/api/tests/test_crawlers_docs.py`, same style as `test_discovery_operations_runbook.py`)

1. `crawl docs mention the kind filter, bounded drain, retry, and manual candidate emit`.
2. `crawl docs state that procedures are not documents`.
3. `crawl docs document the OBJECT_STORE settings, the 503 behaviour and the 507 byte cap`.
4. `crawl docs document the Cloudflare browser budget, the release-on-limit rule, and that the token is not a Render variable`.
5. `the operations docs and the ingest README do not tell anyone to install Playwright or a capture extra` — negative contract for the removed design (the plan folder may name it as a rejected alternative).
6. `crawl docs do not claim link-following, freshness crawling, LLM extraction or requirement emit as shipped` — negative scope contract.
7. `every relative link in the crawlers plan folder, the loop document and the changed runbooks resolves`.
8. `plans README lists twenty-three crawler chapters and no reference to apps/crawler as a package to build`.
9. `crawl docs state the free-allocation caps (R2 bytes and operations, browser seconds, database soft limit) and the 1,000 minute Actions cap, and no document still assumes about 960 minutes as a forward-looking share`.

**Green:** update the documents until the checks pass.

**Refactor:** docs-only; report "no code refactor needed" unless implementation work was pulled in.

## Verification

```bash
cd apps/api && python -m pytest tests/test_crawlers_docs.py tests/test_discovery_docs_sync.py tests/test_discovery_operations_runbook.py
gh pr checks --watch
```

## As built (2026-10-27)

- Tests: `apps/api/tests/test_crawlers_docs.py` (content contracts), `test_crawlers_docs_structure.py` (links, indexes,
  neighbours, checklist) and the helper module `crawlers_docs_support.py`. Several contracts read the code instead of
  repeating it: every API stop reason, every `discovery_task_kind` value and every `object_store_*` setting must appear in
  the runbooks, and every German key in the checklist must exist in the seed.
- Runbooks: `discovery-online.md` was rewritten around the drain (kinds, retry, run report, stop reasons, browser
  budgets, storage limits, triage). It no longer says `remaining` is unknown or that a scheduled run is one batch.
  `discovery-layer.md` gained the crawl flow, candidates, manual emit, routes and the FIM known gap.
- New: `docs/operations/crawlers-operator-checklist.md` (chapter 22's steps with a tick column, what was reported done, what
  is open, the German review list). Chapter 22's text got the same two fixes: the machine header is `X-API-Key`, and the
  probes run on a laptop while `gh workflow run` answers 404 for workflows not yet on `main`.
- Throughput: the stale "about 80 pages per run" in decision D20 and chapter 18 became about 4 pages a minute (55 to 65
  per 900 s run, about 22 runs for the backlog).
- Not changed: the run ledger, other suites' statuses beyond the prescribed notes (evidence-storage chapters 1 and 2 are
  marked absorbed), and any code.

## Out of scope

Rewriting source-canon documents (government endpoint facts stay in `docs/discovery/government-data-sources.md`), editing other suites' statuses, new features.
