---
name: "Chapter 1 — Object-store port and settings"
overview: "An ObjectStore protocol and an InMemoryObjectStore fake, plus the R2/S3 settings fields; no real network client yet. Everything above this layer can be built and tested against the fake."
todos:
  - id: protocol
    content: "ObjectStore protocol"
    status: pending
  - id: fake
    content: "InMemoryObjectStore"
    status: pending
  - id: settings
    content: "Settings: endpoint, bucket, credentials, storage_enabled"
    status: pending
isProject: false
---

# Chapter 1 — Object-store port and settings

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/evidence-object-store-port` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Every later chapter depends on `ObjectStore`, never on boto3 or R2 directly (D2). This chapter defines the
shape and a fully working in-memory implementation.

## Design decisions

**Protocol, not ABC**: `typing.Protocol` with four methods (architecture §3), so the fake and the real
adapter share no base class, only the shape. Keys are opaque strings; callers never inspect their format
here (content-addressing is chapter 4's concern).

**`InMemoryObjectStore`** stores `{key: (bytes, content_type)}` in a plain dict; `get_presigned_url` returns
a fake `memory://{key}` URL (never dereferenced in tests, only asserted); `delete` on a missing key is a
no-op, not an error (matches S3 semantics); `exists` is a plain lookup.

**Settings** (following [config.py](../../../apps/api/app/config.py)'s pattern): `s3_endpoint_url`,
`s3_bucket`, `s3_access_key_id`, `s3_secret_access_key`, `s3_region` (default `auto`, R2's convention), and
`storage_enabled` (true only when endpoint and bucket are both set) — same off-by-default shape as auth
chapter 1's `auth_enabled`.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/evidence/__init__.py` | New package |
| `apps/api/app/features/evidence/object_store.py` | `ObjectStore` protocol |
| `apps/api/app/features/evidence/in_memory_object_store.py` | Fake |
| `apps/api/app/config.py` | Five fields, `storage_enabled` |
| `apps/api/.env.example` | Document the R2 variables |
| `apps/api/tests/test_object_store_protocol.py`, `test_config_storage.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `InMemoryObjectStore · put then get_presigned_url references the same key` | Round trip |
| `InMemoryObjectStore · exists is false before put and true after` | State |
| `InMemoryObjectStore · delete removes the object` | `exists` false afterward |
| `InMemoryObjectStore · delete on an unknown key does not raise` | S3-like semantics |
| `InMemoryObjectStore · put with the same key overwrites content and content_type` | Overwrite |
| `Settings · storage_enabled is false when nothing is configured` | Default |
| `Settings · storage_enabled is true when endpoint and bucket are set` | Positive |
| `Settings · storage_enabled is false with only a bucket` | Partial config |
| `Settings · s3_region defaults to auto` | Default |

## Green

1. Protocol and fake; tests 1–5.
2. Settings fields and property; tests 6–9.

## Refactor gate

Fake stays a single small class; no premature abstraction beyond the protocol. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_object_store_protocol.py tests/test_config_storage.py
cd ../.. && ./ci.sh
```

## Out of scope

Real S3/R2 client (chapter 2), evidence table, endpoints.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/evidence-object-store-port
```

```text
test(api): describe the object store protocol and its in-memory fake

feat(api): add ObjectStore protocol, in-memory fake and storage settings
```
