---
name: "Chapter 4 — Evidence service"
overview: "EvidenceService that hashes bytes, builds the content-addressed key, uploads through the ObjectStore, and records or reuses the evidence row — the point where the object store and the database meet."
todos:
  - id: repo
    content: "EvidenceRepository add and list"
    status: pending
  - id: service
    content: "EvidenceService.attach with hash-based dedupe"
    status: pending
isProject: false
---

# Chapter 4 — Evidence service

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/evidence-service` · **Status:** planned

**Depends on:** [2](02-s3-adapter-and-minio.md), [3](03-evidence-model-migration.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3–4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Given a suggestion id, raw bytes, a kind, a source URL and a fetch time, `EvidenceService.attach(...)`
produces exactly one `Evidence` row and one stored object — twice for identical bytes produces one of each
(D3), not two.

## Design decisions

**Layering.** `EvidenceRepository` (session queries) → `EvidenceService` (hash, key, store, record) →
depends on `SuggestionService.exists(id)` (a new one-line addable method) to 404 early, and on `ObjectStore`
injected at construction — never boto3 directly.

**Steps in `attach`**: `sha256 = hashlib.sha256(data).hexdigest()`; if a row for
(`suggestion_id`, `sha256`) already exists, return it unchanged **without re-uploading** (content-addressing
means the object is already there); otherwise `key = f"evidence/{suggestion_id}/{sha256}.{ext(content_type)}"`,
`store.put(key, data, content_type)`, then insert the row. Upload before insert, so a crash after upload but
before insert just orphans an object (acceptable, seam) rather than leaving a row with no object.

**`ext(content_type)`** is a small fixed dict (`image/png`→`png`, `image/jpeg`→`jpg`, `text/html`→`html`);
an unknown type raises `UnsupportedEvidenceTypeError` before any upload is attempted.

**Size limit** (D8, 8 MB) is checked in the service (`len(data)`), before hashing, so an oversized upload
fails fast without spending CPU on a hash it will discard.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/evidence/repository.py` | `EvidenceRepository` |
| `apps/api/app/features/evidence/service.py` | `EvidenceService`, `ext`, errors |
| `apps/api/app/features/evidence/dependencies.py` | Providers |
| `apps/api/app/features/suggestions/service.py` | `exists(id)` |
| `apps/api/tests/test_evidence_service.py` | Tests below (uses `InMemoryObjectStore`) |

## Red tests

| Test | Asserts |
| --- | --- |
| `EvidenceService.attach · stores the object and records the row` | Store has the key, row matches |
| `EvidenceService.attach · derives the key from suggestion id and content hash` | Key format |
| `EvidenceService.attach · re-attaching identical bytes returns the existing row without re-uploading` | Store `put` called once |
| `EvidenceService.attach · attaching different bytes for the same suggestion creates a second row` | Two rows, two keys |
| `EvidenceService.attach · rejects an unsupported content type before uploading` | Store untouched |
| `EvidenceService.attach · rejects a file over 8 MB before hashing` | Store untouched |
| `EvidenceService.attach · rejects an unknown suggestion id` | 404-mapped error, store untouched |
| `EvidenceService.list · returns evidence for a suggestion ordered by fetched_at` | Order |

## Green

1. Repository; happy path in the service; tests 1–2.
2. Dedupe; tests 3–4.
3. Content-type and size guards; tests 5–6.
4. Suggestion existence; test 7.
5. `list`; test 8.

## Refactor gate

`attach` is four named steps (`_validate`, `_hash_and_key`, `_existing_or_store`, `_record`) of ≈5 LOC each.
Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_evidence_service.py
cd ../.. && ./ci.sh
```

## Out of scope

HTTP multipart handling (chapter 5), presigned reads (chapter 6).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/evidence-service
```

```text
test(api): describe evidence attach with hashing and dedupe

feat(api): add EvidenceService
```
