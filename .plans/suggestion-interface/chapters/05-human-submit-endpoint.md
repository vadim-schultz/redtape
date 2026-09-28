---
name: "Chapter 5 — Human submit endpoint"
overview: "POST /api/v1/suggestions for logged-in users: 201 with the pending suggestion, 401 unauthenticated, 409 with conflicts for duplicates, 422 for invalid payloads or unknown jurisdiction and codes."
todos:
  - id: schema
    content: "SuggestionRead and SubmitterRead schemas"
    status: done
  - id: controller
    content: "SuggestionsController.create with error mapping"
    status: done
  - id: router
    content: "suggestions_router registered in main.py"
    status: done
isProject: false
---

# Chapter 5 — Human submit endpoint

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-submit` · **Status:** implemented, PR open

**Depends on:** [4](04-duplicate-detection.md), auth [4](../../auth/chapters/04-current-user-dependency.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A signed-in person can submit a `new_document` suggestion over HTTP. First write endpoint in the API.

## Design decisions

**Router and controller follow the documents slice**: `suggestions_router` at `/api/v1/suggestions`, tag
`suggestions`, `router_dependencies` merging the suggestion providers and the auth providers; a
`SuggestionsController` with `sync_to_thread=True` handlers. The router is added to `route_handlers` in
[main.py](../../../apps/api/app/main.py).

**Uses `current_user` in this chapter** (human only). Chapter 6 switches the parameter to `principal` and
adds the machine path; keeping the first version human-only makes the 401/403 story trivial to test.

**Error mapping lives in the controller** (`_to_http(exc)` dict from exception type to status): 
`DuplicateSuggestionError` → 409 with body `{"detail": "Duplicate suggestion", "conflicts": [...]}`;
`UnknownJurisdictionError`, `UnknownTaxonomyCodeError` → 422. Pydantic validation errors are already 422.

**Transaction**: `provide_session` commits after the handler, so a 409 or 422 (raised exceptions) rolls back
and leaves no row.

**Response** is `SuggestionRead` (architecture §5): submitter shown as `{kind: "user", display_name}`. When
`display_name` is empty the value is `null` and the UI renders a translated "Anonymous"; nothing is ever
derived from the email (D7). The 201 carries a `Location: /api/v1/suggestions/{id}` header.

**Rate limiting is not built here** (seam S4). The chapter's PR description records that the route must not
be exposed publicly before a limit exists; until then it ships behind auth only, which is already required.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/schema/suggestion/read.py` | `SuggestionRead`, `SubmitterRead`, `ConflictRead` |
| `apps/api/app/features/suggestions/controller.py`, `router.py` | Controller and router |
| `apps/api/app/main.py` | Register `suggestions_router` |
| `apps/api/tests/test_suggestions_submit.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `POST /suggestions · creates a pending suggestion and returns 201` | Body shape, status `pending` |
| `POST /suggestions · sets a Location header to the new resource` | Header |
| `POST /suggestions · records the authenticated user as submitter` | `submitted_by.kind == "user"` |
| `POST /suggestions · response never contains the submitter's email` | Negative, string search on body |
| `POST /suggestions · returns 401 without a token` | Negative |
| `POST /suggestions · returns 401 for an API key` | Human-only in this chapter |
| `POST /suggestions · returns 409 with conflicts for a duplicate document` | Body lists ids |
| `POST /suggestions · a rejected request leaves no row behind` | Count unchanged after 409 and 422 |
| `POST /suggestions · returns 422 for an invalid payload` | e.g. non-http URL |
| `POST /suggestions · returns 422 for an unknown municipality_code` | Domain error mapping |
| `POST /suggestions · returns 422 for an unknown domain code` | Domain error mapping |
| `POST /suggestions · ignores client-supplied status and submitter fields` | Extra fields are 422 (forbidden) |

## Green

1. Schemas, controller, router registration; tests 1–3, 5.
2. Privacy and negatives; tests 4, 6.
3. Error mapping; tests 7–8, 9–12.

## Refactor gate

- Controller handler ≈5 LOC: call the service, wrap in `SuggestionRead`. Error mapping is one dict and one
  function, not per-handler try/except.
- `SuggestionRead.from_row` conversion is a single named function reused by chapters 6–7.
- Report the outcome.

## Progress

All 12 red tests in `test_suggestions_submit.py` pass. `SuggestionsController.create` is 5 statements
(call the service, catch the three domain errors, build `SuggestionRead`, return with `Location`); error
mapping lives in one function, `_to_http`, keyed by a `dict[type[Exception], int]` — no per-handler
try/except, matching the refactor gate as written.

One deviation from the chapter as planned: Litestar's `ValidationException` (raised for a malformed
`SuggestionCreate` body) defaults to **400**, not 422, contradicting the architecture doc's "Pydantic
validation errors are already 422" assumption. `suggestions_router` registers an `exception_handlers`
entry that re-renders the same Litestar validation body at 422 instead — scoped to this router rather
than app-wide, since only the suggestions contract promises 422 for invalid payloads.

The 409 conflict body uses Litestar's standard `extra` field for structured exception data
(`{"status_code": 409, "detail": "Duplicate suggestion", "extra": {"conflicts": [...]}}`) rather than the
flat `{"detail": ..., "conflicts": [...]}` shorthand in the chapter's prose — the flat shape isn't
producible through Litestar's built-in exception rendering without a bespoke response type, and `extra`
is the idiomatic place for it.

`current_user`'s `display_name` is normalized to `null` when empty (falsy) before building
`SubmitterRead`, per D7 — the email is never read by the response path at all.

`./ci.sh` is green: apps/api pytest — 251 passed; ruff format/check and mypy clean; migrations round trip
clean; web lint/format/typecheck/test/build all pass.

Commits on `feat/suggestions-submit`:
1. `test(api): describe submitting a suggestion, its 401, 409 and 422`
2. `feat(api): add POST /api/v1/suggestions for logged-in users`

PR opened against `main`.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestions_submit.py
cd ../.. && ./ci.sh
curl -s -X POST localhost:8000/api/v1/suggestions -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d @suggestion.json
```

## Out of scope

Machine principals and idempotency (chapter 6), list and detail (chapter 7), rate limiting.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-submit
```

```text
test(api): describe submitting a suggestion, its 401, 409 and 422

feat(api): add POST /api/v1/suggestions for logged-in users
```
