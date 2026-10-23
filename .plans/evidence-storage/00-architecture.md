---
name: Evidence Storage — Architecture
overview: "An ObjectStore port with an S3-compatible adapter for Cloudflare R2 (MinIO locally), an evidence table recording what was fetched and when, and an upload/read API so every suggestion can carry a screenshot and the raw page as proof."
isProject: false
---

# Evidence Storage — Architecture

> **Planned amendment (crawlers suite, 2026-10-23).** The [crawlers suite](../crawlers/00-architecture.md) builds the object-store port and S3 adapter itself (its chapter 13, under `apps/api/app/shared/object_store`), with **Supabase Storage first** and Cloudflare R2 as a configuration swap, and stores crawler snapshots and screenshots as staging `discovery_artifact` rows. Chapters 1–2 of this suite are therefore absorbed; the suggestion-keyed `evidence` model, routes and viewer (chapters 3–7) remain here, and bridging `discovery_artifact` objects to `evidence` rows at emit time is an open seam of this suite. Statements below that name R2 as the only provider are superseded by that amendment.

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Why

A suggestion is a claim ("this document exists at this URL"). Moderators cannot verify it from a URL alone
if the page changes or disappears, and a crawler's claim needs proof it looked at the page it says it did.
`docs/planning/01-stack-and-free-tier.md` names Cloudflare R2 or Supabase Storage as options; neither is
configured (verified: no S3/MinIO/boto3 in the repo). This suite picks R2 (program decision D1) and builds
the evidence record the crawler and voting suites both depend on.

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Evidence** | One captured artifact for a suggestion: a screenshot or the raw fetched HTML, with when it was fetched and a content hash. |
| **Object store** | The S3-compatible bucket holding the bytes. Evidence rows hold metadata and a key; the store holds content. |
| **Storage key** | `evidence/{suggestion_id}/{sha256}.{ext}` — content-addressed, so re-uploading identical bytes is a no-op. |

## 3. Design

**Port and adapter** (`apps/api/app/features/evidence/object_store.py`): an `ObjectStore` protocol
(`put(key, data, content_type) -> None`, `get_presigned_url(key, expires_in) -> str`, `delete(key) -> None`,
`exists(key) -> bool`). Two implementations: `S3ObjectStore` (boto3, works against R2 and MinIO — both speak
the S3 API) and `InMemoryObjectStore` (tests). Nothing above this layer imports boto3.

**Local dev and CI**: `docker-compose.yml` gains a `minio` service; `docker-compose` already has no other
services besides `db`. R2 and MinIO differ only in endpoint URL and credentials, both read from `Settings`.

**Upload path is proxied through the API** (D5): the browser and the crawler both `POST` bytes to our
endpoint; the API uploads to the store. Rejected: presigned direct-to-bucket uploads (would put R2
credentials, or a signing endpoint with its own abuse surface, on the crawler and the browser). Reads use a
short-lived presigned GET URL (§6), which is safe to hand out because it only ever points at one object.

## 4. Data model

**`evidence`**

| Column | Notes |
| --- | --- |
| `id` | UUID primary key |
| `suggestion_id` | FK `suggestion.id`, `ondelete=CASCADE`, indexed |
| `kind` | native enum `evidence_kind` (`screenshot`, `html`) |
| `storage_key` | String(300), the object key |
| `sha256` | String(64), content hash |
| `content_type` | String(100) |
| `byte_size` | Integer |
| `source_url` | String(500), the URL that was captured |
| `fetched_at` | timestamptz — **when the content was captured**, distinct from `created_at` (when the row was written); a crawler may capture now and submit evidence minutes later (evidence-storage chapter 5 / crawlers chapter 8) |
| `created_at` | timestamptz, `server_default=func.now()` |

`uq_evidence_suggestion_sha256` unique on (`suggestion_id`, `sha256`): re-uploading identical bytes for the
same suggestion updates nothing new (D-dedupe).

## 5. API contract

| Route | Auth | Purpose |
| --- | --- | --- |
| `POST /api/v1/suggestions/{id}/evidence` | user or API key (D5) | Multipart: `file`, `kind`, `source_url`, `fetched_at` |
| `GET /api/v1/suggestions/{id}/evidence` | public | List, each with a presigned `url` (short TTL) |

Limits: 8 MB per file, content types `image/png`, `image/jpeg`, `text/html`. Errors: 401, 404 (unknown
suggestion), 413 (too large), 415 (wrong content type), 422 (missing field).

## 6. Presigned reads

`get_presigned_url` TTL is 5 minutes (a constant, not a setting, to avoid a long-lived-link footgun). The
list endpoint always mints a fresh URL; nothing durable is ever stored as a public link.

## 7. Layering

`apps/api/app/features/evidence/{object_store.py, s3_object_store.py, repository.py, service.py,
controller.py, router.py, dependencies.py}`, same shape as other features. `EvidenceService` depends on
`SuggestionService` (to confirm the suggestion exists) through its service, never its repository.

## 8. Web

`apps/web/src/features/evidence/` adds an evidence viewer (fetched date, screenshot thumbnail opening full
size, raw-HTML download link) embedded in the suggestion detail page from
[suggestion-interface chapter 10](../suggestion-interface/chapters/10-web-suggestion-list-and-detail.md).

## 9. Out of scope

Video capture, PDF capture, virus scanning, CDN caching of evidence, retention/expiry policy (GDPR seam),
editing or deleting evidence once attached (moderators can only see it), multi-region replication.
