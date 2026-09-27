---
name: "Chapter 2 — S3 adapter and MinIO"
overview: "S3ObjectStore backed by boto3, a MinIO service in docker-compose for local dev and CI, and an integration test proving the same adapter works against it — the code that will run unmodified against R2."
todos:
  - id: dep
    content: "boto3 dependency"
    status: pending
  - id: adapter
    content: "S3ObjectStore implementing the protocol"
    status: pending
  - id: compose
    content: "docker-compose minio service and bucket bootstrap"
    status: pending
isProject: false
---

# Chapter 2 — S3 adapter and MinIO

**Repo:** `redtape` (`apps/api`, `docker-compose.yml`, CI) · **Branch:** `feat/evidence-s3-adapter` · **Status:** planned

**Depends on:** [1](01-object-store-port-and-settings.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`S3ObjectStore` passes the exact same contract test as `InMemoryObjectStore`, running against a real MinIO
container. Swapping the endpoint URL and credentials in production points the identical code at R2 (D1).

## Design decisions

**Shared contract test.** `tests/object_store_contract.py` defines parametrized behaviour
(`put`/`get_presigned_url`/`exists`/`delete`) run against **both** implementations via a fixture factory, so
chapter 1's fake and this adapter are provably interchangeable — this is the test that proves D2 in
practice, not just in code shape.

**boto3 client** built once from settings: `boto3.client("s3", endpoint_url=…, aws_access_key_id=…,
aws_secret_access_key=…, region_name=…)`. R2 needs `config=Config(signature_version="s3v4")`
(Cloudflare's documented requirement); this is set unconditionally since it is also valid for MinIO/AWS.

**`get_presigned_url`** uses `client.generate_presigned_url("get_object", …, ExpiresIn=…)`. Errors from
boto3 (`ClientError`) are wrapped into one `ObjectStoreError` so callers never import botocore exceptions
(keeps the protocol boundary clean).

**MinIO in compose**, alongside `db`: image `minio/minio`, `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`
`minioadmin`/`minioadmin` (local only), console port and API port, healthcheck. A `minio-init` one-shot
service (or a small script called from `ci.sh`) creates the `redtape-evidence` bucket idempotently
(`mc mb --ignore-existing`), since MinIO does not auto-create buckets.

**CI** adds a MinIO service to `api-lint-test.yml` alongside Postgres, with the same bucket-creation step.

## Files

| Path | Change |
| --- | --- |
| `apps/api/pyproject.toml` | `boto3` |
| `apps/api/app/features/evidence/s3_object_store.py` | `S3ObjectStore`, `ObjectStoreError` |
| `apps/api/tests/object_store_contract.py` | Shared contract |
| `apps/api/tests/test_in_memory_object_store_contract.py`, `test_s3_object_store_contract.py` | Instantiations |
| `docker-compose.yml` | `minio` service, bucket bootstrap |
| `.github/workflows/api-lint-test.yml` | MinIO service, bucket bootstrap step |
| `apps/api/.env.example` | Local MinIO defaults documented |

## Red tests

| Test | Asserts |
| --- | --- |
| `contract · put then get_presigned_url yields a URL that serves the bytes` | HTTP GET on the presigned URL (both implementations) |
| `contract · exists reflects put and delete` | Both implementations |
| `contract · put with the same key overwrites content` | Both implementations |
| `contract · presigned URL expires` | Short `expires_in`, wait, 403/expired (S3 only; the fake documents it does not enforce expiry) |
| `S3ObjectStore · wraps a client error in ObjectStoreError` | Bad bucket name |
| `S3ObjectStore · is constructed from Settings without extra wiring` | Factory function |

## Green

1. Contract module parametrized over the fake; existing chapter-1 tests still pass through it.
2. Adapter and factory; run the contract against MinIO; tests 1–3.
3. Expiry test (4) and error wrapping (5–6).
4. Compose and CI wiring.

## Refactor gate

- Adapter methods stay ≈5 LOC by delegating to boto3 directly; only error translation is extra logic.
- Contract test has no per-implementation duplication (one function, two fixtures).
- Report the outcome.

## Verification

```bash
docker compose up -d --wait db minio
cd apps/api
python -m pytest tests/test_in_memory_object_store_contract.py tests/test_s3_object_store_contract.py
cd ../.. && ./ci.sh
```

## Out of scope

Evidence model and endpoints, R2 production credentials (chapter 8).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/evidence-s3-adapter
```

```text
test(api): describe the object store contract against MinIO

feat(api): add S3ObjectStore and a local MinIO service
```
