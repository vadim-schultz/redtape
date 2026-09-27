---
name: "Chapter 8 — Evidence submission"
overview: "EvidenceApiClient uploads a captured screenshot to a created suggestion's evidence endpoint, completing the crawler's write path: submit the candidate, then attach its proof."
todos:
  - id: client
    content: "EvidenceApiClient.upload_screenshot"
    status: pending
isProject: false
---

# Chapter 8 — Evidence submission

**Repo:** `redtape` (`apps/crawler`) · **Branch:** `feat/crawler-evidence-submission` · **Status:** planned

**Depends on:** [2](02-suggestion-api-client.md), [7](07-screenshot-capture.md), evidence-storage [5](../../evidence-storage/chapters/05-evidence-upload-endpoint.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`EvidenceApiClient(base_url, api_key).upload_screenshot(suggestion_id, capture, source_url)` posts the
captured PNG to `/api/v1/suggestions/{id}/evidence`, the second half of the write path per candidate (a
created suggestion, then its evidence).

## Design decisions

**Separate client class from `SuggestionApiClient`**, sharing only the underlying `httpx.Client` and the
`retry` helper (constructed together in the orchestrator, chapter 9) — they hit different endpoints with
different content types (JSON versus multipart) and have different outcome shapes, so merging them would
mean one class doing two things.

**Multipart body** matches evidence-storage's contract exactly (chapter 5 there): `data` (the PNG bytes),
`kind=screenshot`, `source_url`, `fetched_at` (ISO 8601, from the `CapturedScreenshot`).

**Outcome type**: `EvidenceOutcome` = `Attached(evidence_id) | Error(status, body)`. No "duplicate" case
here (evidence dedup is by content hash, evidence-storage D3 — a genuine duplicate simply returns the
existing row with 201, not a 409, so from the crawler's perspective it is indistinguishable from a fresh
attach and needs no special handling).

**Failure here does not undo the suggestion.** If the screenshot upload fails after the suggestion was
created, the suggestion still exists (evidence-less); the orchestrator's report (chapter 9) flags this
distinctly from a total failure, since a suggestion without evidence is still useful for a moderator to
review, just weaker.

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/crawler/evidence_client.py` | `EvidenceApiClient`, `EvidenceOutcome` |
| `apps/crawler/tests/test_evidence_client.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `EvidenceApiClient · uploads a screenshot with the correct multipart fields` | respx request body/fields |
| `EvidenceApiClient · returns Attached with the evidence id on success` | 201 mapping |
| `EvidenceApiClient · returns Error on a 4xx without raising` | Same non-throwing contract as the suggestion client |
| `EvidenceApiClient · retries a 503 then succeeds` | Shared `retry` reused |
| `EvidenceApiClient · sends fetched_at as ISO 8601` | Exact format the API expects |

## Green

1. Client and happy path; tests 1–2.
2. Error and retry; tests 3–4.
3. Timestamp formatting; test 5.

## Refactor gate

Method ≈5 LOC, same shape as `SuggestionApiClient.submit_new_document`. Report the outcome.

## Verification

```bash
cd apps/crawler
python -m pytest tests/test_evidence_client.py -m "not needs_playwright"
```

## Out of scope

Wiring capture and upload together into one flow (chapter 9).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-evidence-submission
```

```text
test(crawler): describe uploading a captured screenshot as evidence

feat(crawler): add EvidenceApiClient
```
