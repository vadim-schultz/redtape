---
name: "Chapter 2 — Suggestion API client"
overview: "SuggestionApiClient wraps httpx to submit suggestions with an API key and an idempotency key, treating 409 as a normal duplicate outcome rather than an error, tested entirely against respx (no real network)."
todos:
  - id: client
    content: "SuggestionApiClient.submit_new_document"
    status: pending
  - id: outcome
    content: "SubmitOutcome distinguishing created/duplicate/error"
    status: pending
isProject: false
---

# Chapter 2 — Suggestion API client

**Repo:** `redtape` (`apps/crawler`) · **Branch:** `feat/crawler-api-client` · **Status:** planned

**Depends on:** [1](01-crawler-package-skeleton.md), suggestion-interface [6](../../suggestion-interface/chapters/06-machine-submit-endpoint.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`SuggestionApiClient(base_url, api_key).submit_new_document(candidate) -> SubmitOutcome`, tested against
[docs/operations/suggestion-api.md](../../../docs/operations/suggestion-api.md)'s contract (written in
suggestion-interface chapter 11) using `respx` to mock the exact HTTP shape, never a real server.

## Design decisions

**`httpx.Client`** (sync, matches the API's own sync stance; no need for async in a scheduled batch job),
constructed once per run with `X-API-Key` and a `User-Agent` header set at the client level, not per call.

**`SubmitOutcome`** is a small tagged union: `Created(suggestion_id)`, `Duplicate(conflicts)`, `Error(status,
body)` — the orchestrator (chapter 9) branches on this type, never on a raw status code, so the "409 is
normal" rule (D7) lives in exactly one place.

**Idempotency key** is computed by the caller (chapter 4/6 supply it: a stable hash of the candidate's
source URL) and passed in as a parameter, not derived inside the client — the client is a thin HTTP
wrapper, key derivation is a domain decision made where the candidate is built.

**`respx` fixtures assert the exact request** the architecture's contract promises: method, path,
`X-API-Key`, `Idempotency-Key`, and the JSON body shape (`kind`, `jurisdiction_id`, `payload`,
`source_url`) — this test suite is the executable check that the crawler and the API agree, since they are
built and tested independently.

**Retries**: transient network errors and 5xx get the same small retry budget as `PoliteFetcher` (chapter
3) will use for fetching, reusing one small `retry(fn, attempts=3)` helper shared between the two (the
`fetcher.py` and `api_client.py` modules both import it from a small `retry.py` — justified now because two
call sites already exist, satisfying the rule of three at introduction rather than waiting for a third).

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/pyproject.toml` | `httpx`, dev extra `respx` |
| `apps/crawler/crawler/retry.py` | `retry(fn, attempts, retry_on)` |
| `apps/crawler/crawler/api_client.py` | `SuggestionApiClient`, `SubmitOutcome` types |
| `apps/crawler/tests/test_api_client.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `SuggestionApiClient · submits a candidate and returns Created on 201` | Body and headers match the contract |
| `SuggestionApiClient · sends the Idempotency-Key header exactly as given` | Header value |
| `SuggestionApiClient · returns Duplicate with conflicts on 409` | Not raised as an exception |
| `SuggestionApiClient · returns Error on 422 with the response body` | Field errors preserved |
| `SuggestionApiClient · returns Error on 401` | No credentials or bad key |
| `SuggestionApiClient · retries once on a 503 then succeeds` | Two requests recorded by respx |
| `SuggestionApiClient · gives up after the retry budget on repeated 503s` | Returns `Error` |
| `retry · does not retry on a 4xx` | Only 5xx/timeout retried |

## Green

1. `retry` helper; test 8.
2. Client happy path and header contract; tests 1–2.
3. Duplicate and error mapping; tests 3–5.
4. Retry wiring; tests 6–7.

## Refactor gate

Client method ≈5 LOC: build the request, call `retry`, map the response. Report the outcome.

## Verification

```bash
cd apps/crawler
python -m pytest tests/test_api_client.py -m "not needs_playwright"
```

## Out of scope

Fetching pages (chapter 3), evidence submission (chapter 8).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-api-client
```

```text
test(crawler): describe submitting suggestions and treating 409 as a duplicate

feat(crawler): add SuggestionApiClient
```
