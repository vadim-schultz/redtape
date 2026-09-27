---
name: "Chapter 5 — Evidence upload endpoint"
overview: "POST /api/v1/suggestions/{id}/evidence accepts a multipart file from a user or an API key and attaches it as evidence, enforcing the size and type limits over HTTP."
todos:
  - id: controller
    content: "Multipart handler on the suggestions evidence sub-route"
    status: pending
  - id: errors
    content: "413/415/404/422 mapping"
    status: pending
isProject: false
---

# Chapter 5 — Evidence upload endpoint

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/evidence-upload-endpoint` · **Status:** planned

**Depends on:** [4](04-evidence-service.md), auth [8](../../auth/chapters/08-machine-principal-guard.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`POST /api/v1/suggestions/{id}/evidence` lets a signed-in person or a crawler holding an API key attach a
screenshot or the raw HTML to a suggestion (D5).

## Design decisions

**Route lives under evidence's own feature**, path `/api/v1/suggestions/{suggestion_id}/evidence`, so the
suggestions feature does not gain evidence-specific code (only its `exists` read, chapter 4). This mirrors
how the matrix endpoint composes documents and taxonomy through services, not routes.

**`principal: Principal`** (auth chapter 8), same either/or as suggestion submission (D1 of the program:
one interface). No role beyond being authenticated is required — any signed-in person may add evidence to
any suggestion (moderation review of evidence quality is a human process, not an access rule).

**Litestar multipart**: `data: UploadFile` for the file, `kind: EvidenceKind`, `source_url: str`,
`fetched_at: datetime` as form fields (`Body(media_type=RequestEncodingType.MULTIPART_FORM_DATA)`). Content
length is checked against the 8 MB limit **before** reading the whole body where the framework allows it
(`request.content_length`); the service's own check (chapter 4) is the second line of defense.

**Errors**: 404 unknown suggestion; 413 oversized (from either the pre-check or the service); 415 wrong
content type; 422 missing/invalid form fields (`fetched_at` not parseable, `source_url` not http(s)). 401 for
no credentials, inherited from the principal dependency.

**Response** is `EvidenceRead` (chapter 6 defines the full read shape); this chapter needs only the fields
that exist without a presigned URL (`id, kind, sha256, content_type, byte_size, source_url, fetched_at,
created_at`) — the URL field is added in chapter 6 without changing this chapter's tests beyond the new key
appearing (documented, not re-asserted).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/schema/evidence/read.py` | `EvidenceRead` (without `url` yet) |
| `apps/api/app/features/evidence/controller.py`, `router.py` | Handler and router at the suggestions sub-path |
| `apps/api/app/main.py` | Register `evidence_router` |
| `apps/api/tests/test_evidence_upload.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `POST .../evidence · a signed-in user uploads a screenshot` | 201, row exists |
| `POST .../evidence · an API key uploads raw HTML` | 201, `kind == "html"` |
| `POST .../evidence · returns 401 without credentials` | Negative |
| `POST .../evidence · returns 404 for an unknown suggestion` | Negative |
| `POST .../evidence · returns 413 for a file over 8 MB` | Pre-check, store untouched |
| `POST .../evidence · returns 415 for an unsupported content type` | e.g. `application/pdf` |
| `POST .../evidence · returns 422 for a missing source_url` | Field error |
| `POST .../evidence · returns 422 for an unparseable fetched_at` | Field error |
| `POST .../evidence · re-uploading identical bytes returns the existing evidence, not a new row` | Dedupe surfaced over HTTP |
| `POST .../evidence · a rejected request leaves no row and no object` | Rollback proof, both layers |

## Green

1. Happy path, both principal kinds; tests 1–3.
2. 404; test 4.
3. Size and type limits; tests 5–6.
4. Field validation; tests 7–8.
5. Dedupe and rollback proof; tests 9–10.

## Refactor gate

Handler ≈5 LOC: build bytes, call the service, wrap the result. Error mapping shares the dict pattern from
suggestions chapter 5. Report the outcome.

## Verification

```bash
docker compose up -d --wait db minio
cd apps/api
python -m pytest tests/test_evidence_upload.py
cd ../.. && ./ci.sh
curl -s -X POST "localhost:8000/api/v1/suggestions/$ID/evidence" -H "Authorization: Bearer $TOKEN" \
  -F "data=@screenshot.png" -F "kind=screenshot" -F "source_url=https://example.org" \
  -F "fetched_at=2026-09-27T10:00:00Z"
```

## Out of scope

Listing and presigned reads (chapter 6), the web viewer (chapter 7).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/evidence-upload-endpoint
```

```text
test(api): describe evidence upload, its limits and its errors

feat(api): add POST /api/v1/suggestions/{id}/evidence
```
