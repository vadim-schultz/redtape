---
name: "Chapter 6 — Machine submit endpoint"
overview: "POST /api/v1/suggestions also accepts an API key; crawler suggestions require source_url, are recorded with source_type crawler, and an Idempotency-Key header makes retries return the original suggestion with 200."
todos:
  - id: principal
    content: "Controller takes principal instead of current_user"
    status: completed
  - id: idempotency
    content: "Idempotency-Key handling in service and controller"
    status: completed
  - id: source-url
    content: "source_url required for crawlers"
    status: completed
isProject: false
---

# Chapter 6 — Machine submit endpoint

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-machine-submit` · **Status:** implemented, PR open

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

## Progress

All 14 red tests in `test_suggestions_machine_submit.py` pass, alongside the unmodified chapter 5 suite
(minus one obsoleted test, see deviations). `SuggestionsController.create` takes `principal` and an
`Idempotency-Key` header parameter; `submitter_ref`/`submitter_display_name` in the new `submitter.py` hold
the only `isinstance` branching on `Principal` in the suite, matching auth chapter 8's "one dispatch table"
guidance.

`SuggestionService.create` grew to: replay-check (early return), `_validate` (jurisdiction + codes +
source_url, bundled to keep `create` itself at five named steps), `_check_duplicates`, then `_build_row` +
`_insert`. `_replay(submitter, idempotency_key)` came out exactly as sketched — one method, reused both for
the initial lookup and, after a caught `IntegrityError`, for the race-recovery re-read. The service stayed
at 93 LOC, under the ~100 LOC refactor-gate threshold, so `SuggestionSubmission` was not extracted.

Three deviations from the chapter as planned:

1. **`create` returns `SubmissionResult(suggestion, replayed)` instead of a bare `Suggestion`.** The
   controller needs to know replay-vs-fresh-insert to answer 200 vs. 201, and the chapter's own idempotency
   design (replay wins over duplicate detection) makes that outcome a first-class thing the service decides,
   not something inferable from the row alone. The alternative — inferring "was this a replay" from
   `created_at` timestamps or a mutable side-channel — was worse than a small typed return value. This
   touched existing white-box tests in `test_suggestion_service.py` and `test_suggestion_duplicates.py`,
   which now read `.suggestion` off the result; their assertions are otherwise unchanged.
2. **`principal` is typed `object` on the controller handler, cast to `Principal` immediately inside.**
   Litestar's msgspec-based signature model cannot validate a handler parameter whose type is a union of two
   dataclasses (`UserPrincipal | MachinePrincipal`) — it raises `TypeError: Type unions may not contain more
   than one dataclass or attrs type` at request time. Auth chapter 8's own test suite already worked around
   this by typing its probe route's parameter as `principal: object`; this chapter follows the same
   precedent rather than inventing a second workaround.
3. **`test_returns_401_for_an_api_key` (chapter 5) is removed.** It asserted that any API key gets 401 on
   this route — true only because chapter 5 required `current_user`. Chapter 6 intentionally makes API keys
   a valid submitter (D1), so the assertion is now false; it's superseded by this chapter's own
   `test_an_api_key_creates_a_crawler_suggestion` (a valid key succeeds) and `test_a_revoked_key_gets_401`
   (only a revoked/unknown key still 401s).

`_validate_url` in `schema/suggestion/payload.py` was renamed to the public `validate_url(value, *,
field=...)` so `source_url` (in `schema/suggestion/create.py`) could reuse the same http/https/length rule
as `official_url`, per the design decision that source_url is "validated like official_url."

The race-recovery path (`_insert`'s `except IntegrityError`) is covered by
`test_a_concurrent_retry_resolves_to_the_original`, which blinds the service's first `_replay` call via
monkeypatch (simulating "not yet visible") while leaving the real `uq_suggestion_key_idempotency` constraint
and the second, real `_replay` call to do the actual race recovery — a real DB constraint violation and real
recovery query, with only the initial miss simulated.

`./ci.sh` is green: apps/api pytest — 264 passed; ruff format/check and mypy clean; migrations round trip
clean; web lint/format/typecheck/test/build all pass.

Commits on `feat/suggestions-machine-submit`:
1. `test(api): describe crawler submission and idempotent retries`
2. `feat(api): accept API keys and Idempotency-Key on suggestion submit`

PR opened against `main`.

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
