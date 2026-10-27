---
name: Evidence Storage — Gaps and decisions
overview: "Settled decisions and open seams for the object store port, the evidence model and the upload and read endpoints."
isProject: false
---

# Evidence Storage — Gaps and decisions

> **Amendment (crawlers suite, built on `feat/crawlers`, 2026-10-27).** The [crawlers suite](../crawlers/00-architecture.md) built the object-store port and the S3 adapter itself, in `app/shared/object_store` ([its chapter 13](../crawlers/chapters/13-object-store-port-and-r2-adapter.md)), with **Cloudflare R2** as the provider, configured through `OBJECT_STORE_*` settings (another S3-compatible service is a configuration change), plus a metered store and a byte cap (its chapters 14 and 23). It stores crawler snapshots and screenshots as staging `discovery_artifact` rows. Chapters 1–2 of this suite are therefore **absorbed** by that work and need no build here. The suggestion-keyed `evidence` model, routes and viewer (chapters 3–7) remain here and keep their meaning. Bridging `discovery_artifact` objects to `evidence` rows at emit time is an open seam of this suite: keys are content-addressed, so the bridge is a copy or a shared key. Statements below about building the port and adapter are superseded.

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **Cloudflare R2** via the S3 API (program decision), confirmed by the [crawlers suite](../crawlers/gaps-and-decisions.md) (its decision D10). The code is provider-neutral: `S3ObjectStore` takes an endpoint URL, so the same adapter runs against R2 in production, `moto` in tests and any other S3-compatible service by configuration. Nothing R2-specific leaks past the adapter. |
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
