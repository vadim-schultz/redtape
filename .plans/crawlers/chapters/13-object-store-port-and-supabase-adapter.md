---
name: "Chapter 13 — Object store port and Supabase adapter"
overview: "An ObjectStore port with in-memory and S3 adapters, optional settings so the API still boots without storage, and a live probe workflow that proves Supabase Storage works."
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

# Chapter 13 — Object store port and Supabase adapter

**Repo:** `redtape` (`apps/api`, `.github/workflows`) · **Branch:** `feat/crawlers-object-store` · **Status:** planned

**Depends on:** [01](01-ingest-ci.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Provide the storage seam that snapshots and screenshots use, without coupling anything to a vendor. This chapter absorbs chapters 1 and 2 of [evidence-storage](../../evidence-storage/01-rollout.md) with Supabase Storage as the first provider; the docs sync (chapter 21) amends that suite.

## Contract

**Location.** `apps/api/app/shared/object_store/` so both discovery and the later evidence suite can import it.

**Port.**

```text
ObjectStore.put(key, data: bytes, content_type) -> None
ObjectStore.get(key) -> bytes                       # raises ObjectNotFoundError
ObjectStore.exists(key) -> bool
ObjectStore.delete(key) -> None                     # idempotent
ObjectStore.presigned_get_url(key, *, expires_in=300, download_name=None) -> str
```

`download_name` adds a `Content-Disposition: attachment` response override so HTML snapshots download instead of rendering. Nothing above this package imports `boto3`.

**Adapters.**

- `InMemoryObjectStore` for tests (`presigned_get_url` returns a deterministic `memory://` URL).
- `S3ObjectStore` using boto3 with path-style addressing, signature v4, the configured endpoint and region, and `request_checksum_calculation` / `response_checksum_validation` set to `when_required` unless the probe shows the default works. Supabase Storage documents support for PutObject, GetObject, HeadObject, DeleteObject and presigned URLs, and lacks Content-MD5, ACLs, versioning and object tagging, so the adapter uses none of those.

**Settings** ([config.py](../../../apps/api/app/config.py)): `object_store_endpoint_url`, `object_store_region`, `object_store_bucket`, `object_store_access_key_id`, `object_store_secret_access_key` (all optional), `object_store_force_path_style` (default true). `Settings.object_store_enabled` is true only when all five required values are set. The presign TTL is a constant (300 s), not a setting.

**Dependency provider.** `get_object_store()` returns an `ObjectStore` or `None`. A helper `require_object_store()` raises `ObjectStoreUnavailableError`, mapped to HTTP 503 with a clear message, for routes that need it (chapter 14). Booting the API with no storage settings must keep working; existing tests must not need any.

**Dependencies.** `boto3` in `apps/api/pyproject.toml`; `moto[s3]` in the dev extra. No Docker or MinIO is needed in CI. A MinIO service in `docker-compose.yml` is optional for local development and not required by any test.

**Probe.** `apps/api/scripts/object_store_probe.py` reads the settings from the environment and, under a unique `probe/<uuid>` prefix, performs put, exists, get, presign (then an unauthenticated HTTP GET of the presigned URL), a second presign with `download_name` (checking the `Content-Disposition` header), delete, and exists-after-delete. It tries the checksum configuration variants and prints a pass/fail table plus the variant it recommends, never the secret values. `.github/workflows/discovery-storage-probe.yml` is `workflow_dispatch` only, installs `apps/api`, and supplies the `OBJECT_STORE_*` values from repository secrets. These are the only GitHub secrets that carry storage credentials (invariant 5).

## TDD loops

### Loop A — Contract on both adapters

**Red** (`apps/api/tests/test_object_store.py`, parametrized over `InMemoryObjectStore` and `S3ObjectStore` on `moto`)

1. `put then get returns the same bytes and content type`.
2. `exists is false before put and true after; delete makes it false again`.
3. `get of a missing key raises ObjectNotFoundError`.
4. `delete of a missing key is a no-op`.
5. `presigned url is minted without a network call and carries the expiry`.

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

Live gate (needs operator steps S1–S4 in [chapter 22](22-operator-manual-steps.md)):

```bash
gh workflow run discovery-storage-probe.yml
gh run watch && gh run view --log
```

All probe steps pass; the recommended checksum variant is recorded in the ledger and set as the adapter default in a follow-up commit if it differs from `when_required`. If the presigned GET step fails, stop and record the finding in [gaps-and-decisions.md](../gaps-and-decisions.md) (the fallback is API-streamed reads instead of presigned URLs, which changes chapters 14 and 16).

## Out of scope

Artifact tables and routes (chapter 14), evidence tables, virus scanning, CDN, retention, multi-region.
