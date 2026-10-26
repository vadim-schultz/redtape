---
name: "Chapter 13 — Object store port and R2 adapter"
overview: "An ObjectStore port with in-memory and S3 adapters (Cloudflare R2 first), optional settings so the API still boots without storage, a metered decorator and a size cap, and a live probe workflow that proves R2 works."
todos:
  - id: port
    content: "ObjectStore protocol, error types, key-agnostic contract"
    status: pending
  - id: adapters
    content: "InMemoryObjectStore and S3ObjectStore (boto3) with a shared contract test suite"
    status: pending
  - id: settings
    content: "OBJECT_STORE_* settings; store optional; dependency provider returns None when unset"
    status: pending
  - id: probe
    content: "object_store_probe script and discovery-storage-probe.yml"
    status: pending
isProject: false
---

# Chapter 13 — Object store port and R2 adapter

**Repo:** `redtape` (`apps/api`, `.github/workflows`) · **Branch:** `feat/crawlers-object-store` · **Status:** planned

**Depends on:** [01](01-ingest-ci.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Provide the storage seam that snapshots and screenshots use, without coupling anything to a vendor. This chapter absorbs chapters 1 and 2 of [evidence-storage](../../evidence-storage/01-rollout.md) with **Cloudflare R2** as the first provider (decision D10, revised 2026-10-26: 10 GB free, free egress, same account as the frontend and Browser Run); the docs sync (chapter 21) amends that suite. R2 **bills** past its free tier, so this chapter also carries the hooks the guards of [chapter 23](23-free-tier-guards.md) need (decision D24).

## Contract

**Location.** `apps/api/app/shared/object_store/` so both discovery and the later evidence suite can import it.

**Port.**

```text
ObjectStore.put(key, data: bytes, content_type) -> None
ObjectStore.get(key) -> bytes                       # raises ObjectNotFoundError
ObjectStore.exists(key) -> bool                     # HEAD: Class B; callers prefer the DB sha256 key
ObjectStore.delete(key) -> None                     # idempotent
ObjectStore.presigned_get_url(key, *, expires_in=300, download_name=None) -> str
```

`download_name` adds a `Content-Disposition: attachment` response override (`ResponseContentDisposition` in the presign) so HTML snapshots download instead of rendering. Nothing above this package imports `boto3`. The port deliberately has **no `list`** (a Class A operation), and callers deduplicate through the database's `(catalogue_service_id, kind, sha256)` unique key, never through `exists`.

**Adapters.**

- `InMemoryObjectStore` for tests (`presigned_get_url` returns a deterministic `memory://` URL).
- `S3ObjectStore` using boto3 with path-style addressing, signature v4, the configured endpoint and region (`auto` for R2), and `request_checksum_calculation` / `response_checksum_validation` set to `when_required` (the default CRC headers of recent boto3 are known to trouble non-AWS stores) unless the probe shows the default works. R2 supports PutObject, GetObject, HeadObject, DeleteObject and presigned URLs on its S3 endpoint (not on a custom domain); the adapter uses no ACLs, versioning, tagging or Content-MD5.
- `MeteredObjectStore(inner, meter)` decorates any store and calls `meter(kind, n)` with `class_a` for `put` and `delete`, `class_b` for `get` and `exists`; presigning is local and costs nothing. The meter is an injected callable (a no-op in this chapter); [chapter 23](23-free-tier-guards.md) supplies the ledger-backed one and the monthly caps. Over a cap the meter raises `ObjectStoreQuotaError`, mapped like `ObjectStoreUnavailableError` (503 on routes, a release on workers).

**Settings** ([config.py](../../../apps/api/app/config.py)): `object_store_endpoint_url` (R2: `https://<account_id>.r2.cloudflarestorage.com`), `object_store_region` (R2: `auto`), `object_store_bucket`, `object_store_access_key_id`, `object_store_secret_access_key` (all optional), `object_store_force_path_style` (default true), and `object_store_max_bytes` (default 8 GiB, enforced by chapter 14). `Settings.object_store_enabled` is true only when all five required values are set. The presign TTL is a constant (300 s), not a setting.

**Dependency provider.** `get_object_store()` returns an `ObjectStore` or `None`. A helper `require_object_store()` raises `ObjectStoreUnavailableError`, mapped to HTTP 503 with a clear message, for routes that need it (chapter 14). Booting the API with no storage settings must keep working; existing tests must not need any.

**Dependencies.** `boto3` in `apps/api/pyproject.toml`; `moto[s3]` in the dev extra. No Docker or MinIO is needed in CI. A MinIO service in `docker-compose.yml` is optional for local development and not required by any test.

**Probe.** `apps/api/scripts/object_store_probe.py` reads the settings from the environment and, under a unique `probe/<uuid>` prefix, performs put, exists, get, presign (then an unauthenticated HTTP GET of the presigned URL), a second presign with `download_name` (checking the `Content-Disposition` header), delete, and exists-after-delete. It tries the checksum configuration variants and prints a pass/fail table plus the variant it recommends, never the secret values. It also confirms that the presigned URL works on the account's S3 endpoint and that the object count it created is zero after cleanup (a leftover object is a Class A operation spent for nothing). `.github/workflows/discovery-storage-probe.yml` is `workflow_dispatch` only, installs `apps/api`, and supplies the `OBJECT_STORE_*` values from repository secrets. These are the only GitHub secrets that carry storage credentials (invariant 5).

## TDD loops

### Loop A — Contract on both adapters

**Red** (`apps/api/tests/test_object_store.py`, parametrized over `InMemoryObjectStore` and `S3ObjectStore` on `moto`)

1. `put then get returns the same bytes and content type`.
2. `exists is false before put and true after; delete makes it false again`.
3. `get of a missing key raises ObjectNotFoundError`.
4. `delete of a missing key is a no-op`.
5. `presigned url is minted without a network call and carries the expiry`.
6. `metered store counts put and delete as class A and get and exists as class B, and presign as nothing` — and `a meter that raises stops the call before the inner store is touched` (negative).

**Green:** implement the protocol, then the two adapters.

**Refactor:** keep adapters under about a hundred lines each; client construction in one factory.

### Loop B — Settings and provider

**Red** (`test_config_object_store.py`)

1. `object store is disabled when any required setting is missing`.
2. `object store is enabled when all settings are present`.
3. `require_object_store raises the unavailable error when disabled, mapped to 503`.
4. `the app boots without object store settings` — import and health check.

**Green:** settings property and provider.

**Refactor:** one place builds the client from settings.

### Loop C — Probe script

**Red** (`test_object_store_probe.py` against `moto`)

1. `probe reports all steps passing against a working store`.
2. `probe reports the failing step and exits non-zero when delete fails`.
3. `probe output never includes the secret access key`.

**Green:** a small script built on the adapter.

**Refactor:** each probe step is a function returning a result row.

## Verification

```bash
cd apps/api && python -m pytest tests/test_object_store.py tests/test_config_object_store.py tests/test_object_store_probe.py
gh pr checks --watch
```

Live gate (needs operator steps S1–S4 in [chapter 22](22-operator-manual-steps.md): R2 bucket, bucket-scoped R2 token, Render variables, probe secrets):

```bash
gh workflow run discovery-storage-probe.yml
gh run watch && gh run view --log
```

All probe steps pass; the recommended checksum variant is recorded in the ledger and set as the adapter default in a follow-up commit if it differs from `when_required`. If the presigned GET step fails, stop and record the finding in [gaps-and-decisions.md](../gaps-and-decisions.md) (the fallback is API-streamed reads instead of presigned URLs, which changes chapters 14 and 16).

## Out of scope

Artifact tables and routes (chapter 14), the ledger and the real meter (chapter 23), evidence tables, virus scanning, CDN or a custom R2 domain, retention, multi-region.
