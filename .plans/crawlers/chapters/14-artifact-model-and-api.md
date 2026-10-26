---
name: "Chapter 14 — Artifact model and API"
overview: "Persist artifact metadata, accept uploads from workers through the API, serve snapshot bytes back to workers, expose presigned URLs to the admin, and add the queue groundwork the Cloudflare browser kinds need: the render_page label, result_note, release and a storage status route."
todos:
  - id: model
    content: "discovery_artifact table; artifact_id on tasks and mentions"
    status: pending
  - id: upload
    content: "POST /machine/tasks/{id}/artifacts with server-side hashing, limits, idempotency, snapshot retention"
    status: pending
  - id: read
    content: "Machine content and list routes; admin list with presigned URLs"
    status: pending
  - id: coverage
    content: "Artifact counts and bytes in coverage"
    status: pending
  - id: browser-groundwork
    content: "render_page enum label, result_note, release route, storage status route"
    status: pending
isProject: false
---

# Chapter 14 — Artifact model and API

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/crawlers-artifact-api` · **Status:** planned

**Depends on:** [13](13-object-store-port-and-r2-adapter.md), [03](03-kind-filtered-claim.md) · **Followed by:** [23](23-free-tier-guards.md) (ledger and operation caps) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Workers need a place to put page snapshots and screenshots and a way to read snapshots back; the admin needs to see them. The database holds metadata only; bytes live in the object store (decision D9). The same migration carries the small queue changes that [chapter 15](15-cloudflare-render-and-snapshot.md) needs to run browser tasks on Cloudflare's free plan (decisions D19–D21), so the API ships one migration for the whole artifact path.

## Contract

**Migration.** New table `discovery_artifact` (enum `DiscoveryArtifactKind` = `html_snapshot|screenshot`): `id`, `catalogue_service_id` (FK cascade), `discovery_task_id` (FK set null), `kind`, `storage_key String(300)`, `sha256 String(64)`, `content_type String(100)`, `byte_size Integer`, `source_url String(500)`, `final_url String(500) NULL`, `fetched_at timestamptz`, `created_at`. Unique `(catalogue_service_id, kind, sha256)`. Also `discovery_task.artifact_id` (FK set null) and the deferred `discovery_candidate_mention.artifact_id` foreign key (set null).

The same migration adds `discovery_task.result_note String(200) NULL` (moved here from chapter 17; the vocabulary starts with `no_extractor`, `no_mentions`, `login_wall`, `oversize`) and `ALTER TYPE discovery_task_kind ADD VALUE IF NOT EXISTS 'render_page'` inside `op.get_context().autocommit_block()`. The downgrade drops the columns and leaves the label (enum labels cannot be removed), as in chapter 3. Update the hard-coded head in `tests/test_discovery_staging_migration_retry.py` and `tests/test_check_migrations_script.py`. Round trip must pass `scripts/check_migrations.sh`.

**Key.** `discovery/{catalogue_service_id}/{kind}/{sha256}.{ext}` with `ext` from the content type (`html`, `png`, `jpg`). Content-addressed, so re-uploading identical bytes is a no-op at the store.

**Upload route.** `POST /api/v1/discovery/machine/tasks/{task_id}/artifacts`, multipart with `file`, `kind`, `source_url`, optional `final_url`, and `fetched_at`.

- The server computes the sha256 itself; any client-supplied hash is ignored.
- Limits and types: `html_snapshot` is `text/html` up to 4 MB (a rendered DOM is larger than the raw HTML; decision D12); `screenshot` is `image/png` or `image/jpeg` up to 8 MB. Violations are 415 (type) or 413 (size).
- Unknown task is 404. The catalogue row comes from the task.
- An identical artifact returns the existing row with 200; a new one returns 201.
- After inserting an `html_snapshot`, prune to the latest two per catalogue row (rows first, objects best-effort; an orphaned object is accepted and noted in the gaps). Screenshots are never pruned.
- If the object store is not configured the route returns 503 and writes nothing.
- **Size cap (decision D24).** R2 bills past its free tier, so before writing the route compares `SUM(discovery_artifact.byte_size) + incoming size` with `object_store_max_bytes` (chapter 13, default 8 GiB). Over the cap it answers **507** and writes nothing (no object, no row). The sum is one indexed aggregate, not an object-store call. Identical re-uploads do not grow the sum and stay 200.
- **No existence probe.** The route finds an existing artifact through the unique key `(catalogue_service_id, kind, sha256)` and calls `put` only for a new one, so re-uploads cost no Class A or Class B operation.

**Machine read routes.** `GET /api/v1/discovery/machine/artifacts/{id}/content` streams the bytes with the stored content type (extractors need it; 4 MB maximum). `GET /api/v1/discovery/machine/artifacts?kind=&host=&limit=` lists metadata (limit at most 100) so the fixture-capture workflow in chapter 17 can find snapshots.

**Enqueue route extension.** `POST /machine/tasks` (chapter 3) accepts an optional `artifact_id` and validates that it exists and belongs to the same catalogue row.

**Admin routes.** `GET /api/v1/discovery/admin/catalogue/{id}/artifacts` returns metadata and a presigned `url` per artifact (five-minute expiry; HTML snapshots get an attachment disposition so they download). Presigning is local computation, so listing is cheap. If storage is unset the list still returns metadata with `url: null`.

**Coverage.** The coverage response gains `artifacts` with count and total bytes per kind plus `bytes_cap`, used by chapter 16.

**Queue groundwork for browser tasks** (used by chapters 15, 17 and 19).

- `POST /machine/tasks/{id}/complete` accepts an optional `{note}` (at most 200 characters, else 422) stored in `result_note`; the admin task DTO exposes it. Existing callers send no body and behave as before.
- `POST /machine/tasks/{id}/release` with `{reason, not_before?}`: only a `claimed` task can be released (409 otherwise, 404 unknown). It returns the task to `pending`, clears the lease and claim, **decrements `attempt_count` (never below zero)** so the claim that is being undone does not count towards `MAX_ATTEMPTS`, sets `last_error = reason`, and sets `not_before` when given. This is how a worker hands back work it could not start because the Cloudflare quota or the object store was unavailable (decision D21). It records a `task_released` event.
- `GET /machine/artifacts/status` returns `{storage_enabled: bool, bytes_used: int, bytes_cap: int}` with no side effects, so a worker can refuse to spend browser time while uploads would answer 503 or 507 (`storage_enabled` is false when the store is unset **or** `bytes_used` has reached the cap).

## TDD loops

All route tests override the store dependency with `InMemoryObjectStore`.

### Loop A — Model

**Red** (`test_discovery_models.py`)

1. `artifact unique per catalogue kind and sha256`.
2. `deleting a catalogue row cascades its artifacts; deleting a task nulls the reference`.

**Green:** model and migration.

**Refactor:** shared mixins; enum exported in `__init__.py`.

### Loop B — Upload

**Red** (`apps/api/tests/test_discovery_artifacts_api.py`)

1. `upload stores bytes under the content-addressed key and returns 201`.
2. `identical upload returns 200 and the same artifact id`.
3. `server ignores a client-supplied hash` — mismatched hash does not change the key.
4. `upload rejects a wrong content type (415) and an oversize file (413)`.
5. `upload for an unknown task is 404`.
6. `upload returns 503 and writes no row when the store is unset`.
7. `third snapshot prunes the oldest; screenshots are never pruned`.
8. `upload over the byte cap returns 507 and writes no object and no row; an identical re-upload under a full cap still returns 200` (negative and happy pair for D24).
9. `a re-upload of an existing sha256 makes no store call` — asserted with a store that fails on any operation.

**Green:** service method per step (validate, hash, put, insert, prune).

**Refactor:** limits live in one table keyed by kind; the controller stays thin.

### Loop C — Reads

**Red**

1. `content route returns the exact bytes and content type`.
2. `content route is 404 for an unknown artifact and 503 when the store is unset`.
3. `admin list returns presigned urls; html urls carry an attachment disposition`.
4. `admin list returns metadata with a null url when storage is unset`.
5. `machine list filters by kind and host and caps the limit`.
6. `routes require the machine key or an admin respectively`.
7. `enqueue with an artifact from another catalogue row is rejected`.

**Green:** repository queries and DTOs.

**Refactor:** reuse the admin paging dependency; one DTO for artifact metadata.

### Loop D — Coverage

**Red** (`test_discovery_coverage.py`) `coverage reports artifact counts and bytes per kind, zero when empty`. **Green/Refactor:** extend the grouped query.

### Loop E — Browser groundwork

**Red** (`test_discovery_task_queue.py`, `test_discovery_machine_api.py`, `test_discovery_admin_api.py`)

1. `render_page can be enqueued, claimed with an explicit kinds filter, and is ignored by the default claim`.
2. `complete stores an optional note and the admin task exposes it; a note over 200 characters is rejected; completing without a body still works`.
3. `release returns a claimed task to pending without consuming an attempt` — claim twice with a release in between and assert `attempt_count`.
4. `release of a task that is not claimed is 409 and an unknown task is 404`.
5. `a released task is claimable again once not_before has passed and not before` — reuses the chapter 4 `claimable` predicate.
6. `artifacts status reports storage_enabled true with a store and false without or when the cap is reached, includes bytes_used and bytes_cap, and requires the machine key`.

**Green:** one `TaskQueue.release` method beside `complete` and `fail`; the status route reads `get_object_store()`. **Refactor:** `release`, `fail` and `complete` share the lease-clearing lines.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_artifacts_api.py tests/test_discovery_models.py tests/test_discovery_coverage.py tests/test_discovery_task_queue.py tests/test_discovery_machine_api.py tests/test_discovery_admin_api.py
cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
gh pr checks --watch
```

Live gate: needs operator steps S1–S4. After deploy, `gh workflow run discovery-storage-probe.yml` is already green (chapter 13); chapter 15 provides the first real upload. Until then record "migration applied; 503 behaviour confirmed with storage unset".

## Out of scope

Worker upload and render code (chapter 15), UI (chapter 16), linking artifacts to suggestion evidence rows, deleting artifacts from the admin, automatic release of stale leases (reclaim keeps its chapter 4 behaviour).
