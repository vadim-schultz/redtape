---
name: "Chapter 15 — Snapshot on fetch"
overview: "Make fetch_url keep what it fetched: upload successful HTML responses as snapshot artifacts, without ever turning a storage problem into a fetch failure."
todos:
  - id: upload-client
    content: "Client method for the artifact upload route"
    status: pending
  - id: handler
    content: "fetch_url uploads text/html 200 responses within the size cap"
    status: pending
  - id: degrade
    content: "Storage unavailable skips the snapshot and is counted, never fails the task"
    status: pending
  - id: ordering
    content: "Document the drain ordering and the re-pend step"
    status: pending
isProject: false
---

# Chapter 15 — Snapshot on fetch

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/crawlers-snapshot-on-fetch` · **Status:** planned

**Depends on:** [02](02-fetcher-hardening.md), [14](14-artifact-model-and-api.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

[`_handle_fetch_url`](../../../apps/discovery-ingest/discovery_ingest/worker/drain.py) downloads the body and discards it. Nothing downstream can extract or show a page. This chapter stores the HTML so chapters 17 and 18 can extract from it and the admin can show it.

## Contract

- After a fetch that ends with status 200, content type `text/html` and a body within 2 MB, the handler uploads the bytes as an `html_snapshot` through `POST /machine/tasks/{id}/artifacts` with `source_url = task.target_url`, `final_url = outcome.final_url` and `fetched_at` set to the fetch instant (UTC, captured before the upload).
- The fetch log row is still appended first, and the task still completes or fails exactly as before; the snapshot never changes the task outcome.
- **Degradation.** A 503 (storage unconfigured), a network error on upload, or a 413/415 is recorded as `snapshot_skipped` with the reason in the drain report (a new counter beside `skipped`) and a log line. It does not fail the task and does not fail the run. A 4xx other than 413/415 is a programming error and fails the task non-retryably.
- Bodies of other types, or over the cap, are not uploaded (no skipped count for "not HTML").
- A hook `after_snapshot(task, artifact)` is called with the new artifact; here it does nothing. Chapter 17 plugs the extractor enqueue into it. The hook keeps the fetch handler free of extractor knowledge.
- `DiscoveryMachineClient.upload_artifact(task_id, kind, data, content_type, source_url, final_url, fetched_at)` returns the artifact id and whether it was created.

## Drain ordering (important)

Snapshots are only captured for pages fetched **after** the object store is live. The 1,323 pending fetch tasks must not be drained before that, or every page needs a second fetch. Therefore the daily scheduled drain from chapter 5 is gated by a repository variable (`DISCOVERY_DRAIN_SCHEDULE=enabled`) that the operator sets after this chapter's live gate passes. This chapter also raises the drain step in `platform-maintenance.yml` to the multi-batch bounds chapter 5 defined for `discovery-drain.yml`. Already completed or failed fetch tasks are re-pended by the operator step S14 in [chapter 22](22-operator-manual-steps.md) so they are fetched again with snapshots.

## TDD loops

### Loop A — Upload on success

**Red** (`apps/discovery-ingest/tests/test_worker_drain.py`, `test_snapshot_upload.py`)

1. `fetch_url uploads an html snapshot after a 200 text/html response` — assert multipart fields including `final_url` and `fetched_at`.
2. `fetch_url does not upload non-html or over-limit bodies`.
3. `fetch_url does not upload a failed fetch`.

**Green:** a small `_snapshot_if_html(outcome)` step after the log append.

**Refactor:** keep `_handle_fetch_url` at about five lines by moving log, snapshot and settle into named steps.

### Loop B — Degradation

**Red**

1. `snapshot upload 503 is counted as snapshot_skipped and the task still completes`.
2. `snapshot upload network error does not fail the task or the run`.
3. `snapshot upload 4xx other than 413 or 415 fails the task without retry`.
4. `drain report includes the snapshot_skipped count`.

**Green:** catch the client's typed error at one boundary.

**Refactor:** the tally gains the counter; the report assembly stays in one function.

### Loop C — Hook

**Red** `after_snapshot receives the created artifact exactly once and is not called when no snapshot was stored`. **Green/Refactor:** pass the hook through handler construction, not a module global.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_worker_drain.py tests/test_snapshot_upload.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate (needs S1–S4 and S14):

```bash
gh workflow run discovery-drain.yml -f kinds=fetch_url -f max_tasks=10 -f max_batches=1
gh run view --log                      # report: completed N, snapshot_skipped 0
```

Then open the pipeline detail of one fetched row in the admin (the panel arrives in chapter 16) or call `GET /api/v1/discovery/admin/catalogue/<id>/artifacts` and confirm an `html_snapshot` with a working presigned URL. Record the run ID and the artifact id.

## Out of scope

Extraction (chapter 17), screenshots (chapter 19), backfilling snapshots for old tasks by anything other than the operator re-pend, rendering snapshots in the UI.
