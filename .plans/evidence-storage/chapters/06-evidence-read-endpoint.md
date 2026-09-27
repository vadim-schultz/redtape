---
name: "Chapter 6 — Evidence read endpoint"
overview: "Public GET /api/v1/suggestions/{id}/evidence lists a suggestion's evidence with a freshly minted, short-lived presigned URL for each item."
todos:
  - id: url
    content: "EvidenceRead gains url, minted per request"
    status: pending
  - id: controller
    content: "GET handler"
    status: pending
isProject: false
---

# Chapter 6 — Evidence read endpoint

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/evidence-read-endpoint` · **Status:** planned

**Depends on:** [5](05-evidence-upload-endpoint.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5–6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Anyone can see what evidence a suggestion has and view it, without ever holding a durable link to the
bucket (D6).

## Design decisions

**No auth** (D7's spirit: suggestions are public for review, so is their evidence). `EvidenceService.list`
(chapter 4) already returns rows ordered by `fetched_at`; this chapter adds `url =
store.get_presigned_url(storage_key, expires_in=EVIDENCE_URL_TTL_SECONDS)` per row, computed in the
controller (a store call, an HTTP-adjacent concern) not the service, keeping the service free of
presentation detail.

**`EVIDENCE_URL_TTL_SECONDS = 300`**, a module constant next to the controller (D6: not a setting — a
constant that changes only with a code review).

**Cache-Control: no-store** on the response, since every response mints fresh URLs that would be wrong to
cache.

**Empty list, not 404**, for a suggestion with no evidence yet (consistent with documents' empty-list
behaviour); 404 is still returned for an unknown suggestion id.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/schema/evidence/read.py` | `EvidenceRead.url`, `EvidenceListResponse` |
| `apps/api/app/features/evidence/controller.py` | `GET` handler |
| `apps/api/tests/test_evidence_read.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `GET .../evidence · lists evidence ordered by fetched_at` | Order |
| `GET .../evidence · each item has a presigned url that serves the bytes` | Fetch the URL, compare bytes |
| `GET .../evidence · returns an empty list for a suggestion with none` | Not 404 |
| `GET .../evidence · returns 404 for an unknown suggestion` | Negative |
| `GET .../evidence · needs no authentication` | Public |
| `GET .../evidence · response is not cacheable` | Header |
| `GET .../evidence · two requests mint different presigned URLs` | Freshness |

## Green

1. `url` field and controller wiring; tests 1, 3–5.
2. Presigned URL correctness; tests 2, 7.
3. Header; test 6.

## Refactor gate

Handler ≈5 LOC: list, map to read models with URLs via a one-line comprehension. Report the outcome.

## Verification

```bash
docker compose up -d --wait db minio
cd apps/api
python -m pytest tests/test_evidence_read.py
cd ../.. && ./ci.sh
curl -s "localhost:8000/api/v1/suggestions/$ID/evidence"
```

## Out of scope

Web viewer (chapter 7).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/evidence-read-endpoint
```

```text
test(api): describe listing evidence with presigned URLs

feat(api): add GET /api/v1/suggestions/{id}/evidence
```
