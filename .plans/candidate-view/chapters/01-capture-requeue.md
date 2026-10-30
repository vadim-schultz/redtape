---
name: "Chapter 1 — Capture requeue and machine route"
overview: "Add a read-only machine route that lists the catalogue rows with candidate mentions and the newest snapshot of each, and a capture requeue command that enqueues capture_screenshot for the pages that lack a screenshot, so the chief of staff can collect the first screenshots."
todos:
  - id: machine-route
    content: "GET /machine/candidates/sources: catalogue rows with at least one mention, newest html_snapshot, screenshot flag, paged with total"
    status: pending
  - id: ingest-client
    content: "Machine client method and schema for the route"
    status: pending
  - id: capture-requeue
    content: "capture requeue command (--host, --limit, --dry-run) reusing the capture enqueue request"
    status: pending
  - id: docs
    content: "Route table, ingest README and docs-sync test mention the route and the command"
    status: pending
isProject: false
---

# Chapter 1 — Capture requeue and machine route

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`, docs) · **Branch:** `feat/candidate-view-capture-requeue` · **Status:** planned  
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 10) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Live run that follows:** [../02-live-runs.md](../02-live-runs.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

On 2026-10-30 production had no screenshot. `llm_extract` queues a `capture_screenshot` task only after it posts mentions ([`worker/capture_enqueue.py`](../../../apps/discovery-ingest/discovery_ingest/worker/capture_enqueue.py), called from `worker/llm_extract.py`), the kind is in no default drain list, and **no tool can enqueue a capture for a page that was already extracted**. The machine API also has no route that links a catalogue row to its candidate mentions, so a repair tool cannot tell which pages were categorised (decision D14).

After this chapter the chief of staff can list the categorised pages without a screenshot and queue a capture for each, idempotently, then drain them ([02-live-runs.md](../02-live-runs.md)).

## Contract

### Machine route

`GET /api/v1/discovery/machine/candidates/sources` on `DiscoveryCandidateMachineController` ([`candidate_machine_controller.py`](../../../apps/api/app/features/discovery/candidate_machine_controller.py), beside `select_candidates` at l.49). It must be declared so the static path `/sources` is not shadowed by the `/{candidate_id:uuid}/...` routes (the `uuid` converter already prevents it; a test pins it).

| Query | Meaning |
| --- | --- |
| `missing` | Optional, only value `screenshot`: keep rows with no `screenshot` artifact. Absent: every row with a mention. Any other value is a 422. |
| `host` | Optional, lower-case host of the snapshot's `source_url`; same matching rule as `GET /machine/artifacts?host=`. |
| `candidate_id` | Optional UUID: keep only the rows that carry a mention of this candidate. The curation run (chapter 11, LR2) uses it to find the procedure page of a candidate it saw in the public list, because the public API hides catalogue ids. Unknown id: empty page; non-UUID: 422. |
| `catalogue_service_id` | Optional, repeatable (at most 20): keep only these procedures. Used by the curation run to capture the pages of chosen candidates first. An unknown id simply matches nothing; a non-UUID is a 422. |
| `offset`, `limit` | `PageParams` (limit 1 to 100, default 20). |

Response `CandidateSourceListResponse` `{items, total, offset, limit}` (schema in `app/schema/discovery/`), item `CandidateSourceRead`:

| Field | Meaning |
| --- | --- |
| `catalogue_service_id` | The procedure (UUID). |
| `source_url` | `source_url` of the **newest** `html_snapshot` artifact of that row; the page the screenshot should capture. |
| `host` | Host of `source_url`. |
| `has_screenshot` | True when the row has at least one `screenshot` artifact. |
| `mention_count` | Candidate mentions on that row. |

A row without an `html_snapshot` is **not listed** (nothing to capture; harvested PVOG rows). Order: `mention_count` descending, then `catalogue_service_id` (deterministic across pages). `total` counts the filtered rows. Read-only, machine-key guarded like its neighbours; no write to any table.

### Machine client

`DiscoveryMachineClient.list_candidate_sources(host, missing, candidate_id, service_ids, offset, limit)` returns a pydantic `CandidateSourcePage` (`items`, `total`, ...), mirroring `list_artifacts` and its schema location.

### `capture requeue`

New command `python -m discovery_ingest capture requeue` in a new module `discovery_ingest/capture_requeue.py`, wired in `cli.py` next to `("llm", "requeue")` (l.377) with a `register_capture_parser`. Same shape as [`llm_requeue.py`](../../../apps/discovery-ingest/discovery_ingest/llm_requeue.py):

- `--host` optional; `--service-id UUID` optional and repeatable (at most 20), passed as `catalogue_service_id` to the route; `--limit` 1 to 200, default 50 (`_limit_arg` reused or shared; do not copy it a third time: move it to a small shared module if a second user appears, rule of three counts the arms); `--dry-run` counts and makes no enqueue call.
- Selection: page through `list_candidate_sources(host, missing="screenshot")` until `limit` rows are gathered.
- Enqueue: `TaskEnqueueRequest(catalogue_service_id, kind="capture_screenshot", target_url=source_url, priority=CAPTURE_PRIORITY, input_key=CAPTURE_INPUT_KEY)`. Build it with a small function extracted from `capture_enqueue.py` (`capture_request(catalogue_service_id, target_url)`) that `enqueue_screenshot_for_mentions` also uses, so the priority and key exist once.
- Report on stdout, one line: `pages=N queued=N already_queued=N failed=N` and `dry_run=true` when set. Exit 1 when `failed` is non-zero; API errors go through `failing_with_api_error("capture requeue", ...)`.
- It needs only `DISCOVERY_API_URL` and `DISCOVERY_API_KEY`. It does **not** need Cloudflare settings or storage (it only enqueues; the drain checks those).
- Identity is (catalogue row, kind, URL, `shot@1`), so repeated runs report `already_queued` and never duplicate.

## Red tests

API (`apps/api/tests/test_discovery_candidate_sources_api.py`, fixtures as in `test_discovery_candidates_api.py` and `test_discovery_artifacts_api.py:604-675`, machine key helper of the existing machine tests):

| Test | Asserts |
| --- | --- |
| `sources lists a mentioned row with its newest snapshot url` | Two snapshots on one row: the newer `source_url` is returned; `mention_count` and `host` are right; `total` is 1. |
| `sources missing=screenshot hides rows that have a screenshot` | Two mentioned rows, one with a `screenshot` artifact: only the other is returned and `has_screenshot` is false; without `missing` both are returned. |
| `sources filters by host` | Rows on two hosts; `host=` returns one. |
| `sources filters by candidate` | Two candidates on different rows; `candidate_id=` returns only the rows that mention it, with the right `catalogue_service_id`; an unknown id returns an empty page and a non-UUID is a 422 (negative). |
| `sources filters by catalogue service id` | Three mentioned rows; two `catalogue_service_id` values return exactly those two; a non-UUID value is a 422 (negative). |
| `sources omits rows without a mention or without a snapshot` | Negative: a row with a snapshot but no mention, and a row with a mention but no snapshot, are absent. |
| `sources pages deterministically` | `limit=1` over equal mention counts returns each row once across pages; `total` constant. |
| `sources rejects an unknown missing value` | Negative: `missing=snapshot` is 422; `limit=0` and `limit=101` are rejected. |
| `sources requires the machine key` | Negative: no key 401, wrong key 401/403 as the neighbouring machine tests assert. |

Ingest (`apps/discovery-ingest/tests/test_capture_requeue.py`, with the fake transport used by `test_llm_requeue.py` if present; otherwise `httpx.MockTransport`):

| Test | Asserts |
| --- | --- |
| `capture requeue enqueues one capture per source row` | Two rows: two `POST /tasks` with `kind=capture_screenshot`, `priority=300`, `input_key=shot@1`, `target_url` = the row's `source_url`; report `pages=2 queued=2 already_queued=0 failed=0`. |
| `capture requeue counts a known key as already queued` | The API answers `created=false`: `already_queued=1`, `queued=0`, exit 0. |
| `capture requeue dry run makes no enqueue call` | `--dry-run` prints `pages=N queued=0 ... dry_run=true` and sends only the list call. |
| `capture requeue stops at the limit across pages` | 150 rows over two pages with `--limit 120`: exactly 120 enqueue calls. |
| `capture requeue reports failures and exits 1` | Negative: an enqueue 5xx counts `failed=1`, exit code 1, the rest are still tried. |
| `capture requeue rejects a bad limit` | Negative: `--limit 0` and `--limit 201` exit with an argparse error before any call. |
| `capture request is shared with the extraction hook` | `capture_request` produces the request `enqueue_screenshot_for_mentions` sends (priority and key identical). |

Docs:

| Test | Asserts |
| --- | --- |
| `discovery docs list the sources route and capture requeue` | `tests/test_discovery_docs_sync.py` (extend) finds `/machine/candidates/sources` in the route table of `docs/operations/discovery-layer.md` and `capture requeue` in `apps/discovery-ingest/README.md`; negative: removing either makes the test fail (assert on the strings, as the existing sync test does). |

Write and run these pairs before implementing.

## Green

1. API: add `CandidateSourceRead`, `CandidateSourceListResponse` (`app/schema/discovery/`), a repository function `list_candidate_sources(filter, page)` under `features/discovery/repository/` (a new small module, e.g. `candidate_sources.py`, composed in `composite.py:21-37`; `tests/test_discovery_repository_split.py` stays green), a thin service method, and the controller route. The query joins mentions grouped by `catalogue_service_id`, picks the newest `html_snapshot` per row (`DISTINCT ON (catalogue_service_id) ... ORDER BY fetched_at DESC, id DESC` or a window), and an `EXISTS` for a `screenshot` artifact. Host filtering reuses the host expression of `repository/artifact_listing.py`.
2. Ingest: client method and `CandidateSourcePage`; `capture_request` extracted; `capture_requeue.py`; CLI wiring and help text.
3. Docs: add the route to the table at `docs/operations/discovery-layer.md` (l.283-302) and the command to the "Browser kinds" section (l.170-177) and the `apps/discovery-ingest/README.md` command list (l.105-120); extend the docs-sync test. Also one line in `docs/operations/discovery-online.md` (laptop drain): run `capture requeue` then drain `capture_screenshot`.

## Files

**Edit**

- `apps/api/app/features/discovery/candidate_machine_controller.py`, `router.py`/`dependencies.py` only if a new provider is needed
- `apps/api/app/features/discovery/repository/composite.py` and a new `repository/candidate_sources.py`
- `apps/api/app/schema/discovery/` (new `candidate_sources.py` or the existing read module, whichever keeps files under 100 lines)
- `apps/api/tests/test_discovery_candidate_sources_api.py` (new), `tests/test_discovery_docs_sync.py`
- `apps/discovery-ingest/discovery_ingest/api_client.py`, `schemas.py`, `cli.py`, `worker/capture_enqueue.py`, new `capture_requeue.py`
- `apps/discovery-ingest/tests/test_capture_requeue.py` (new)
- `docs/operations/discovery-layer.md`, `docs/operations/discovery-online.md`, `apps/discovery-ingest/README.md`

**Do not edit**

- The drain, the handler (`worker/capture.py`), budgets, default drain kinds (`capture_screenshot` stays out of them), the guards, the models, any migration
- The workflows under `.github/`

## Refactor gate

Audit `candidate_machine_controller.py` (class size, parameters per method, one nesting level), `cli.py` (command table and parser registration stay table-driven), `capture_enqueue.py` (one source for priority and key) and the new repository module (about 5 lines per function, about 100 per file, strict types, docstrings on public items for ruff pydocstyle). Report what was extracted or "audited, nothing needed".

## Verification

```bash
cd apps/api && pytest tests/test_discovery_candidate_sources_api.py tests/test_discovery_docs_sync.py tests/test_discovery_repository_split.py
cd ../discovery-ingest && pytest tests/test_capture_requeue.py tests/test_llm_wiring.py tests/test_capture_worker.py
cd ../.. && ./ci.sh
```

The route is not live until the owner deploys the API; the live run checks it ([02-live-runs.md](../02-live-runs.md), precondition 2).

## Commits

`test(api): define the candidate sources machine route`, `feat(api): list mentioned catalogue rows for screenshot capture`, `test(ingest): define capture requeue`, `feat(ingest): add capture requeue`, `docs: record the sources route and capture requeue`.

## Out of scope

Draining (the live run does it), enqueueing in bulk from a workflow, a `discovery-render.yml` change, a screenshot status column, re-capturing a page that already has a screenshot, choosing pages by tags or completeness.
