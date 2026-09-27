---
name: "Chapter 6 — Machine submit endpoint"
overview: "POST /api/v1/suggestions also accepts an API key; crawler suggestions require source_url, are recorded with source_type crawler, and an Idempotency-Key header makes retries return the original suggestion with 200."
todos:
  - id: principal
    content: "Controller takes principal instead of current_user"
    status: pending
  - id: idempotency
    content: "Idempotency-Key handling in service and controller"
    status: pending
  - id: source-url
    content: "source_url required for crawlers"
    status: pending
isProject: false
---

# Chapter 6 — Machine submit endpoint

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-machine-submit` · **Status:** planned

**Depends on:** [5](05-human-submit-endpoint.md), auth [8](../../auth/chapters/08-machine-principal-guard.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3, §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A crawler holding an API key submits through the same route and the same validation as a person (D1), and
can safely retry after a timeout without creating a second suggestion (D8).

## Design decisions

**Switch the dependency, not the handler.** The handler parameter changes from `current_user` to
`principal: Principal` (auth chapter 8). A small mapper `submitter_ref(principal) -> SubmitterRef` converts
either principal into the value the service already takes (chapter 3); there is no `isinstance` branching in
the controller.

**`Idempotency-Key` header** (optional for humans, recommended for crawlers). The service, before running
duplicate detection, looks up (`submitted_by_api_key_id`, `idempotency_key`); a hit returns the stored
suggestion and the controller answers **200** instead of 201. The lookup and the unique constraint from
chapter 1 together handle a concurrent retry: on `IntegrityError` for that constraint the service re-reads
and returns the original.

**Idempotency wins over duplicate detection.** A retry of an already-accepted suggestion must return it, not
409 (the first attempt made the suggestion a "pending duplicate of itself"). Order: idempotency lookup,
then duplicates, then insert.

**Keys are only honoured for API keys.** For a human principal the header is ignored (the human unique
constraint does not exist, D8); ignoring, not rejecting, keeps clients simple.

**`source_url` is required for crawlers** (D9): missing → 422 with a field error. It is validated like
`official_url` (http/https, ≤ 500) and stored as given; `normalized_url` still derives from the payload's
`official_url`.

**Key header length** ≤ 128 characters, printable ASCII; longer or invalid → 422.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/suggestions/controller.py` | `principal`, header parameter, 200 vs 201 |
| `apps/api/app/features/suggestions/service.py` | Idempotency lookup, race handling |
| `apps/api/app/features/suggestions/repository.py` | `get_by_idempotency_key` |
| `apps/api/app/features/suggestions/submitter.py` | `submitter_ref(principal)` |
| `apps/api/tests/test_suggestions_machine_submit.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `POST /suggestions · an API key creates a crawler suggestion` | 201, `source_type == "crawler"` |
| `POST /suggestions · crawler submitter is shown without the key or its hash` | Body has `kind: "crawler"`, name only |
| `POST /suggestions · a crawler without source_url gets 422` | Field error on `source_url` |
| `POST /suggestions · a human without source_url is accepted` | Negative pair |
| `POST /suggestions · replaying an Idempotency-Key returns 200 and the same id` | No second row |
| `POST /suggestions · replay with a different body still returns the original` | Documented behaviour |
| `POST /suggestions · the same Idempotency-Key from another API key creates a new suggestion` | Scoping |
| `POST /suggestions · idempotent replay wins over the duplicate check` | 200, not 409 |
| `POST /suggestions · a genuinely different suggestion with a duplicate URL still gets 409` | Without matching key |
| `POST /suggestions · Idempotency-Key is ignored for humans` | Two human posts, second is 409 by duplicates |
| `POST /suggestions · an oversized Idempotency-Key gets 422` | 129 characters |
| `POST /suggestions · a concurrent retry resolves to the original` | Simulated `IntegrityError` path returns the stored row |
| `POST /suggestions · both Authorization and X-API-Key give 400` | Inherited ambiguity rule |
| `POST /suggestions · a revoked key gets 401` | Inherited |

## Green

1. Swap to `principal` and the mapper; tests 1, 2, 13, 14 (human tests from chapter 5 stay green).
2. `source_url` rule; tests 3, 4.
3. Idempotency lookup and 200; tests 5–8, 10, 11.
4. Race path; test 12. Duplicate regression; test 9.

## Refactor gate

- Idempotency is one service method `_replay(submitter, key)` returning `Suggestion | None`; `create` stays
  ≈ four named steps.
- The controller does not know about keys beyond passing the header value through.
- If the service grows past ~100 LOC, extract `SuggestionSubmission` (a handler object holding the
  replay/duplicate/insert steps). Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestions_machine_submit.py tests/test_suggestions_submit.py
cd ../.. && ./ci.sh
curl -s -X POST localhost:8000/api/v1/suggestions -H "X-API-Key: $KEY" -H "Idempotency-Key: demo-1" \
  -H 'Content-Type: application/json' -d @crawler-suggestion.json   # run twice: 201 then 200
```

## Out of scope

Evidence upload (evidence-storage suite), per-key quotas, batch submission.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-machine-submit
```

```text
test(api): describe crawler submission and idempotent retries

feat(api): accept API keys and Idempotency-Key on suggestion submit
```
