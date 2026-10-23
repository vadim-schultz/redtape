---
name: Crawlers — Architecture
overview: "A queue-based, document-first crawl layer on top of the discovery staging path: new task kinds in the existing discovery_task table, page snapshots and screenshots in an object store, deduplicated document candidates with provenance, and admin screens to review documents and their evidence."
isProject: false
---

# Crawlers — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/) · **Ledger:** [run-ledger.md](run-ledger.md) · **Parents:** [discovery-layer](../discovery-layer/00-architecture.md), [discovery-online](../discovery-online/00-architecture.md), [discovery-operations](../discovery-operations/00-architecture.md)

This suite replaces the earlier crawlers plan (a standalone `apps/crawler` package with `sources.yaml` and direct suggestion posts). That design predates the discovery layer, which now owns the queue, staging, deduplication, preview and manual emit. The crawl layer is a **consumer of that queue**, not a parallel pipeline.

## 1. Why

The goal of redtape is a **document dependency graph**: which documents a citizen needs before another document can be obtained. The graph needs document *nodes* before it can have *edges*, so the first job of crawling is to populate documents.

Production data from 2026-10-23 (Supabase SQL) shows what the pipeline produces today:

| Observation | Meaning |
| --- | --- |
| 1,423 `fetch_url` tasks: 1,323 pending, 88 completed, 12 failed; one drain run of 50 tasks | At the scheduled cadence (one 50-task drain per six days) the backlog takes months |
| 81 of 88 completed fetches are HTML 200; 7 are 301/302/307 | The fetcher does not follow redirects, so redirects are recorded as success |
| Fetch bodies are discarded; only status, content type and length are logged | Nothing downstream can be extracted or shown |
| 0 entities, 0 claims; no GovData row has `fim_id`, all 893 have `leika_key` | `enrich_metadata` never fires; fanout looks for the wrong key |
| 123 distinct hosts; GovData `portal_url` values are OZG online-service entry points (one is a login URL with a nonce) | Per-host extractors are a long tail; many pages are login walls |
| PVOG `raw_payload.details[]` holds structured xZufi modules (title, text, `links[]`, `filled`) | Candidate documents can be read from data already in the database, with no network call |
| `suggestion`: 2 human rows; `document`: 4 seeded rows; `document_requirement`: 3 | Nothing crawler-made exists downstream yet |

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Procedure** | A catalogue service (a Leistung such as "Anmeldung einer Wohnung"). A procedure is staging context, not a document node |
| **Document candidate** | A deduplicated, not yet emitted document name harvested from one or more sources; keyed by the same slug rule used at promotion |
| **Mention** | One occurrence of a candidate in a procedure, with role, excerpt, source field and optional artifact |
| **Role** | `required` (the procedure asks for this document) or `form` (a form or application belonging to the procedure) |
| **Artifact** | An object-store file with a metadata row: an HTML snapshot (working input) or a screenshot (evidence) |
| **Extractor** | Worker code that turns one snapshot into mentions; selected by URL and content type |
| **Task kind** | The `discovery_task.kind` value that selects a worker handler |
| **Kind filter** | The `kinds` list a worker sends when claiming, so it only leases work it can perform |

## 3. Flow

```mermaid
flowchart LR
  cat[CatalogueService] -->|fanout| fetch[fetch_url]
  cat -->|fanout| harvest[harvest_payload]
  cat -->|fanout| enrich[enrich_metadata]
  fetch --> snap[(HTML snapshot)]
  snap --> extract[extract_page]
  harvest --> mention[Mentions]
  extract --> mention
  mention --> cand[Document candidates]
  extract -->|at least one mention| shot[capture_screenshot]
  shot --> evid[(Screenshot)]
  cand --> review[Admin review]
  review -->|manual emit| sugg[Pending new_document suggestion]
  sugg -.->|votes and promotion, existing| doc[Document]
```

Workers own orchestration and API owns persistence. A worker that finishes a task and knows what comes next enqueues the follow-up through an idempotent machine route. The API never needs to know which extractors exist.

## 4. Task kinds

All kinds live in the existing `discovery_task` table. New kinds extend the native `discovery_task_kind` enum with `ALTER TYPE ... ADD VALUE` inside an Alembic autocommit block; the downgrade leaves the labels in place and documents it.

| Kind | Network | Input | Output |
| --- | --- | --- | --- |
| `fetch_url` (existing) | yes | `portal_url` | fetch log, HTML snapshot artifact |
| `enrich_metadata` (existing) | yes | FIM steckbrief URL | entity and claims |
| `harvest_payload` (new) | no | catalogue row `raw_payload` | mentions |
| `extract_page` (new) | no | HTML snapshot artifact | mentions |
| `capture_screenshot` (new) | yes, browser | page URL | screenshot artifact |

**Kind-filtered claim.** `TaskClaimRequest` gains `kinds`. When omitted it defaults to the two legacy kinds, so the scheduled drain can never lease a kind it cannot handle and fail it. Today `claim_pending` ([task_queue.py](../../apps/api/app/features/discovery/task_queue.py)) and `list_pending_tasks_for_claim` ([repository/tasks.py](../../apps/api/app/features/discovery/repository/tasks.py)) have no kind filter.

**Task inputs.** `discovery_task` gains nullable `artifact_id` and `input_key` (for example `extractor@version`). The queue's "a completed task for the same target is never re-enqueued" rule then no longer blocks re-extraction after an extractor changes.

**Retry.** `attempt_count`, `not_before` and a `retryable` flag on fail. Transient failures (5xx, timeout, connection reset) return to `pending` with backoff up to a cap. Client errors stay failed.

**Result note.** `discovery_task.result_note` (chapter 17) records why a task completed without producing anything (`no_extractor`, `no_mentions`, `login_wall`). Columns arrive where first used: `input_key` in chapter 3, `attempt_count` and `not_before` in chapter 4, `artifact_id` in chapter 14, `result_note` in chapter 17.

## 5. Document-first strategy

1. **Harvest** candidate nodes: PVOG payload first (no network), then page extractors.
2. **Deduplicate** by a key equal to `slugify(pick_title(title_i18n))`, the exact rule `NewDocumentHandler.promote` uses, so a candidate collision is a promotion collision.
3. **Review** in the admin Documents screens: titles, mention counts, excerpts, evidence.
4. **Emit manually** as pending `new_document` suggestions. Votes and promotion already exist in the API ([handlers.py](../../apps/api/app/features/suggestions/handlers.py), [transitions.py](../../apps/api/app/features/suggestions/transitions.py)); a web voting UI does not exist yet and is outside this suite.
5. **Edges later.** Mentions with roles preserve the procedure-to-document `requires` relation. Resolving mentions to canonical documents and emitting `new_requirement` suggestions is a later suite; it needs promoted documents to reference.

Procedures are **not** document nodes. The FIM enrichment claims that carry a service title as `new_document` stay staged and are excluded from this path.

### Emit and URL conflicts

`new_document` suggestions conflict on `slug` or normalized `official_url` per jurisdiction, and the payload currently requires `official_url`. Many candidates (for example "Personalausweis") have no URL of their own, and sharing the procedure page URL would reject every second document from the same page. The emit chapter therefore makes `official_url` **optional** in `NewDocumentPayload` (additive): URL conflict checks are skipped when it is absent, `Document.official_url` is already nullable, and provenance travels in `suggestion.source_url`.

## 6. Storage

Both artifact kinds live in an S3-compatible object store; Postgres holds only metadata. The free Supabase database is capped at 500 MB, whereas the free Storage allowance is 1 GB with a 50 MB per-file limit, so a full bucket only stops uploads and a full database is far worse.

- **Provider:** Supabase Storage through its S3 API (endpoint `https://<project_ref>.storage.supabase.co/storage/v1/s3`, path-style, project region). Presigned URLs, HeadObject and DeleteObject are supported. Cloudflare R2 remains a configuration swap.
- **Port and adapters:** `ObjectStore` protocol with `InMemoryObjectStore` (tests) and `S3ObjectStore` (boto3). Adapter tests use `moto`, so CI needs no Docker. Checksum behaviour of recent boto3 against Supabase is settled by a live probe workflow.
- **Optional at boot:** if no object-store settings exist the API still starts; artifact routes answer 503.
- **Uploads are proxied** through the API; storage credentials live only in Render. Reads use a short-lived (five-minute) presigned GET minted per request.
- **Keys are content-addressed:** `discovery/{catalogue_service_id}/{kind}/{sha256}.{ext}`.
- **HTML snapshots are never rendered inline** in the admin UI; they are offered as download or source view. The screenshot is the visual.
- **Snapshots are working input** (latest two per service, 2 MB cap, `text/html` only). **Screenshots are evidence** (durable, 8 MB cap, PNG or JPEG). The two `kind` values stay distinct so retention can differ later.

## 7. Staging tables (new)

**`discovery_artifact`**: `id`, `catalogue_service_id` (FK, cascade), `discovery_task_id` (FK, set null), `kind` (`html_snapshot`, `screenshot`), `storage_key`, `sha256`, `content_type`, `byte_size`, `source_url`, `final_url`, `fetched_at`, `created_at`. Unique on `(catalogue_service_id, kind, sha256)`.

**`discovery_document_candidate`**: `id`, `jurisdiction_id`, `key` (unique per jurisdiction), `title_i18n`, `official_url` (nullable), `status` (`staged`, `emitted`), `suggestion_id` (nullable), timestamps.

**`discovery_candidate_mention`**: `id`, `candidate_id` (FK, cascade), `catalogue_service_id` (FK, cascade), `role`, `excerpt`, `source_field`, `artifact_id` (nullable), `extractor`, `extractor_version`, `created_at`. Unique on `(candidate_id, catalogue_service_id, role, source_field)`.

## 8. Worker runtime and scheduling

- The HTTP workers stay in `apps/discovery-ingest` and never receive `DATABASE_URL`.
- Playwright lives in the same package behind an optional extra (`[capture]`) and runs only in its own GitHub Actions workflow with `--kinds capture_screenshot`. There is no `apps/crawler` package; the API image never carries a browser.
- `discovery-drain.yml` drains the HTTP kinds with multiple batches and a time budget (chapters 2 and 5); its daily schedule is gated by the repository variable `DISCOVERY_DRAIN_SCHEDULE` so the backlog is not consumed before snapshots exist. A separate `discovery-capture.yml` (variable `DISCOVERY_CAPTURE_SCHEDULE`) runs the browser workflow. `platform-maintenance.yml` keeps the six-day catalogue ingest.
- Manual probe and fixture workflows (`discovery-storage-probe.yml`, `discovery-fim-probe.yml`, `discovery-fixture-capture.yml`) exist so live verification needs only `gh workflow run`.
- Politeness: robots.txt per host, an identifying User-Agent with a contact URL, a per-host minimum interval, redirect following (maximum five) with the final URL recorded, a body size cap, a content-type allowlist, scheme and private-address blocking, and no attempt to get past login walls.

## 9. Admin surface

Allowlisted, read-only, behind the existing server admin probe.

- **Menu:** one unbroken row of `react-icons` buttons inside a single `HStack`; every new link is added to the config array, never as a new row or a text link (chapter 9).
- **Documents** (`/admin/discovery/documents`): candidate list with filters, mention counts and status.
- **Document detail** (`/admin/discovery/documents/:id`): mentions with role, excerpt and procedure link, artifacts, emit and suggestion status.
- **Pipeline detail:** an Artifacts panel with snapshot download and screenshot thumbnails.
- **Tasks and Coverage:** kind filter, per-kind counts, attempts, candidate counts and storage bytes.

## 10. Out of scope

Link-following frontier crawling, freshness crawling, LLM extraction, PDF parsing, CAPTCHA or login-wall handling, resolving mentions to canonical documents, emitting `new_requirement` suggestions, a web voting UI, attaching artifacts to suggestions as `evidence` rows (the [evidence-storage](../evidence-storage/00-architecture.md) suite owns that bridge).
