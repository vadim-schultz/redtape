---
name: "Chapter 3 — Repository and service"
overview: "SuggestionRepository and SuggestionService that create a pending new_document suggestion, resolving the jurisdiction and validating taxonomy codes through the owning services; wired as feature dependencies."
todos:
  - id: repo
    content: "SuggestionRepository add and get"
    status: done
  - id: docs-service
    content: "DocumentService.resolve_jurisdiction_id (read-only, additive)"
    status: done
  - id: service
    content: "SuggestionService.create for new_document"
    status: done
  - id: deps
    content: "features/suggestions/dependencies.py"
    status: done
isProject: false
---

# Chapter 3 — Repository and service

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-service` · **Status:** implemented, PR open

**Depends on:** [1](01-suggestion-model-migration.md), [2](02-new-document-payload-schema.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4, §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Domain logic for creating a suggestion, testable without HTTP: given a principal, a request and a session, a
`pending` row exists with the derived fields filled in.

## Design decisions

**Layering (tdd-workflow).** `SuggestionRepository` talks to the session only. `SuggestionService` talks to
its repository, to `DocumentService` (jurisdiction) and to `TaxonomyService` (codes). It never imports
`DocumentRepository` or taxonomy models. Rejected: a helper query joining `jurisdiction` directly in the
suggestion repository (crosses the feature boundary).

**Small additive method on documents.** `DocumentService.resolve_jurisdiction_id(jurisdiction_id,
municipality_code) -> UUID | None` wraps the existing private `_effective_jurisdiction_id` and adds an
existence check for a raw `jurisdiction_id` (new `DocumentRepository.jurisdiction_exists`). Existing methods
and tests do not change.

**Errors are domain exceptions**, not HTTP: `UnknownJurisdictionError`, `UnknownTaxonomyCodeError` (wrapping
`TaxonomyCodeError`). The controller maps both to 422 in chapter 5.

**The principal is passed in as a value** (`SubmitterRef(kind, id)`), not as a request object; the service
maps `kind` to the right foreign-key column with a two-entry dict (`{"user": …, "crawler": …}`), not an
if-chain.

**Derived fields set here**: `normalized_url = normalize_url(payload.official_url)` for `new_document`;
`status = pending`; `source_type` from the submitter kind. The client cannot set any of them.

**Provider wiring**: `provide_suggestion_repository`, `provide_suggestion_service`, and
`router_dependencies` merging documents and taxonomy dependencies, as documents already merges taxonomy's.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/suggestions/repository.py` | `SuggestionRepository` |
| `apps/api/app/features/suggestions/service.py` | `SuggestionService`, `SubmitterRef`, errors |
| `apps/api/app/features/suggestions/dependencies.py` | Providers |
| `apps/api/app/features/documents/service.py`, `repository.py` | `resolve_jurisdiction_id`, `jurisdiction_exists` |
| `apps/api/tests/test_suggestion_service.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `SuggestionService.create · stores a pending human suggestion for a user` | Status, source_type, user FK |
| `SuggestionService.create · stores a pending crawler suggestion for an API key` | Source and key FK |
| `SuggestionService.create · derives normalized_url from official_url` | Stored value |
| `SuggestionService.create · resolves municipality_code to the jurisdiction id` | Column value |
| `SuggestionService.create · rejects an unknown jurisdiction_id` | `UnknownJurisdictionError` |
| `SuggestionService.create · rejects an unknown municipality_code` | Same error |
| `SuggestionService.create · rejects an unknown domain code` | `UnknownTaxonomyCodeError` |
| `SuggestionService.create · rejects an unknown situation code` | Pair of the previous |
| `SuggestionService.create · ignores client-supplied status and source_type` | Cannot be forged |
| `SuggestionService.get · returns None for an unknown id` | Negative |
| `DocumentService.resolve_jurisdiction_id · existing behaviour unchanged for documents list` | Existing tests stay green |

## Green

1. Repository add/get; `create` for the human happy path (test 1).
2. Crawler path through the submitter map; test 2.
3. Jurisdiction resolution and errors; tests 4–6.
4. Taxonomy validation; tests 7–8.
5. Derived fields; tests 3, 9, 10.

## Refactor gate

- `create` orchestrates named steps (`_resolve_jurisdiction`, `_validate_codes`, `_build_row`) of ≈5 LOC each.
- Class stays ≤ ~100 LOC; list/filter methods arrive in chapter 7 and, if the class grows, move to a
  `SuggestionQuery` object.
- Report the outcome.

## Progress

All 11 tests in `test_suggestion_service.py` pass, plus `test_documents_filter.py` (existing
`DocumentService`/`list_documents` behaviour unchanged by the additive `resolve_jurisdiction_id`).
The test for "ignores client-supplied status and source_type" asserts the boundary one level up:
`SuggestionCreate.model_validate` rejects a payload carrying `status`/`source_type` keys (the
schema's `extra="forbid"`), since the service's `create(submitter, request)` signature never takes
those fields from the client to begin with — `status` and `source_type` come only from
`SuggestionStatus.PENDING` and the `SubmitterRef.kind → SuggestionSource` map in `_build_row`.

`create` orchestrates three ≈5-8 LOC steps (`_resolve_jurisdiction`, `_validate_codes`,
`_build_row`); the class is 78 lines total, well under the ~100 LOC soft cap, so no refactor was
needed beyond that split. `./ci.sh` (lint, format, mypy, migrations, pytest — 225 passed, web — 233
passed) is green.

Commits on `feat/suggestions-service`:
1. `test(api): describe creating pending suggestions with derived fields`
2. `feat(api): add suggestion repository and service`

PR opened against `main`.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestion_service.py tests/test_documents_filter.py
cd ../.. && ./ci.sh
```

## Out of scope

Duplicate detection (chapter 4), HTTP (chapters 5–7), requirement payloads (chapter 8).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-service
```

```text
test(api): describe creating pending suggestions with derived fields

feat(api): add suggestion repository and service
```
