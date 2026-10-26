---
name: Evidence Storage — Gaps and decisions
overview: "Settled decisions and open seams for the object store port, the evidence model and the upload and read endpoints."
isProject: false
---

# Evidence Storage — Gaps and decisions

> **Planned amendment (crawlers suite, 2026-10-23).** The [crawlers suite](../crawlers/00-architecture.md) builds the object-store port and S3 adapter itself (its chapter 13, under `apps/api/app/shared/object_store`), with **Cloudflare R2** as the provider (revised 2026-10-26: the crawlers plan first said Supabase Storage, then moved to R2; this suite's original choice of R2 stands) and a metered, byte-capped store (its chapters 13, 14 and 23), and stores crawler snapshots and screenshots as staging `discovery_artifact` rows. Chapters 1–2 of this suite are therefore absorbed; the suggestion-keyed `evidence` model, routes and viewer (chapters 3–7) remain here, and bridging `discovery_artifact` objects to `evidence` rows at emit time is an open seam of this suite. Statements below about building the port and adapter are superseded by that amendment; those about R2 as the provider hold.

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **Cloudflare R2** via the S3 API (program decision). `S3ObjectStore` takes an endpoint URL, so the same code runs against R2 in production and MinIO locally/CI — nothing R2-specific leaks past the adapter. |
| D2 | **Port and adapter, not a direct boto3 call site.** Every caller depends on the `ObjectStore` protocol; tests use `InMemoryObjectStore`. Swapping providers later (or adding Supabase Storage) touches one file. |
| D3 | **Content-addressed keys** (`evidence/{suggestion_id}/{sha256}.{ext}`). Re-uploading identical bytes is idempotent by construction; no separate dedupe pass is needed. |
| D4 | **`fetched_at` is caller-supplied, `created_at` is server-set.** A crawler's capture time and its submission time can differ; both matter for evidence credibility. |
| D5 | **Upload is proxied through the API.** Credentials for R2 never reach a browser or a GitHub Actions runner. Rejected: presigned PUT (adds a second authenticated endpoint just to mint upload URLs, for a marginal cost saving that does not matter at this volume). |
| D6 | **Presigned GET, short TTL (5 minutes), minted fresh per list request.** Never store a durable public URL. |
| D7 | **Evidence belongs to a suggestion, not to a document.** Once a suggestion is approved, its evidence stays linked to it (history), and is not copied onto the resulting `Document`. |
| D8 | **8 MB per file, PNG/JPEG/HTML only.** Generous enough for a full-page screenshot, small enough to keep the free-tier bucket cheap. |

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Retention and deletion | None — evidence is kept indefinitely | `security-privacy-gdpr` strand: a user's crawl evidence may need deletion on request |
| Orphaned objects if a DB write fails after upload | Accepted (object without a row); a periodic sweep is not built | Storage cost becomes noticeable |
| Virus/malware scanning of uploaded HTML | None | First abuse report |
| CDN in front of presigned URLs | None; direct-to-R2 | Latency or cost complaints |
| Bridge from crawler `discovery_artifact` rows to suggestion `evidence` rows | None; artifacts stay linked to staging (content-addressed keys allow a shared key or a copy) | Moderators need the crawl screenshot on the suggestion detail page |
| Multiple evidence files per fetch (e.g. screenshot + HTML together) | Modeled as two independent `evidence` rows sharing `source_url`/`fetched_at` | If a "capture" needs its own identity, add a `capture` parent row |
