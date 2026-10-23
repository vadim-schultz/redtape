---
name: "Chapter 14 — Artifact model and API"
overview: "Persist artifact metadata, accept uploads from workers through the API, serve snapshot bytes back to workers, and expose presigned URLs to the admin."
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
isProject: false
---

# Chapter 14 — Artifact model and API

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/crawlers-artifact-api` · **Status:** planned

**Depends on:** [13](13-object-store-port-and-supabase-adapter.md), [03](03-kind-filtered-claim.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Workers need a place to put page snapshots and screenshots and a way to read snapshots back; the admin needs to see them. The database holds metadata only; bytes live in the object store (decision D9).

## Contract

**Migration.** New table `discovery_artifact` (enum `DiscoveryArtifactKind` = `html_snapshot|screenshot`): `id`, `catalogue_service_id` (FK cascade), `discovery_task_id` (FK set null), `kind`, `storage_key String(300)`, `sha256 String(64)`, `content_type String(100)`, `byte_size Integer`, `source_url String(500)`, `final_url String(500) NULL`, `fetched_at timestamptz`, `created_at`. Unique `(catalogue_service_id, kind, sha256)`. Also `discovery_task.artifact_id` (FK set null) and the deferred `discovery_candidate_mention.artifact_id` foreign key (set null). Round trip must pass `scripts/check_migrations.sh`.

**Key.** `discovery/{catalogue_service_id}/{kind}/{sha256}.{ext}` with `ext` from the content type (`html`, `png`, `jpg`). Content-addressed, so re-uploading identical bytes is a no-op at the store.

**Upload route.** `POST /api/v1/discovery/machine/tasks/{task_id}/artifacts`, multipart with `file`, `kind`, `source_url`, optional `final_url`, and `fetched_at`.

- The server computes the sha256 itself; any client-supplied hash is ignored.
- Limits and types: `html_snapshot` is `text/html` up to 2 MB; `screenshot` is `image/png` or `image/jpeg` up to 8 MB. Violations are 415 (type) or 413 (size).
- Unknown task is 404. The catalogue row comes from the task.
- An identical artifact returns the existing row with 200; a new one returns 201.
- After inserting an `html_snapshot`, prune to the latest two per catalogue row (rows first, objects best-effort; an orphaned object is accepted and noted in the gaps). Screenshots are never pruned.
- If the object store is not configured the route returns 503 and writes nothing.

**Machine read routes.** `GET /api/v1/discovery/machine/artifacts/{id}/content` streams the bytes with the stored content type (extractors need it; 2 MB maximum). `GET /api/v1/discovery/machine/artifacts?kind=&host=&limit=` lists metadata (limit at most 100) so the fixture-capture workflow in chapter 17 can find snapshots.

**Enqueue route extension.** `POST /machine/tasks` (chapter 3) accepts an optional `artifact_id` and validates that it exists and belongs to the same catalogue row.

**Admin routes.** `GET /api/v1/discovery/admin/catalogue/{id}/artifacts` returns metadata and a presigned `url` per artifact (five-minute expiry; HTML snapshots get an attachment disposition so they download). Presigning is local computation, so listing is cheap. If storage is unset the list still returns metadata with `url: null`.

**Coverage.** The coverage response gains `artifacts` with count and total bytes per kind, used by chapter 16.

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

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_artifacts_api.py tests/test_discovery_models.py tests/test_discovery_coverage.py tests/test_discovery_task_queue.py
cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
gh pr checks --watch
```

Live gate: needs operator steps S1–S4. After deploy, `gh workflow run discovery-storage-probe.yml` is already green (chapter 13); chapter 15 provides the first real upload. Until then record "migration applied; 503 behaviour confirmed with storage unset".

## Out of scope

Worker upload code (chapter 15), UI (chapter 16), linking artifacts to suggestion evidence rows, deleting artifacts from the admin.
