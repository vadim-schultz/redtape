---
name: "Chapter 8 — Requirement-edge kind"
overview: "Suggestions of kind new_requirement propose that one existing document requires another; validated against existing documents in the jurisdiction, with duplicate detection against existing edges and pending edge suggestions."
todos:
  - id: payload
    content: "NewRequirementPayload joins the discriminated union"
    status: pending
  - id: service
    content: "Kind dispatch table in SuggestionService"
    status: pending
  - id: duplicates
    content: "Edge duplicate rules and partial unique index"
    status: pending
isProject: false
---

# Chapter 8 — Requirement-edge kind

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-requirement-kind` · **Status:** planned

**Depends on:** [5](05-human-submit-endpoint.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The dependency tree (a passport application requires a birth certificate) grows through the same
interface. This is the second kind, and the moment the service needs a real per-kind dispatch.

## Design decisions

**Rule of three, at two.** With two kinds the per-kind behaviour (validate, derive fields, find conflicts)
moves from inline `if kind == …` into a **dispatch table** `KIND_HANDLERS: dict[SuggestionKind, KindHandler]`
with a `KindHandler` protocol (`validate`, `derive`, `conflicts`). The `new_document` code from chapters
3–4 is moved into `NewDocumentHandler` **first** (behaviour-preserving refactor commit with the existing
tests green), then `NewRequirementHandler` is added. A third kind is one class plus one table entry.

**Payload**: `NewRequirementPayload {parent_document_id, required_document_id, notes_i18n?}`; ids are UUIDs,
must differ; `notes_i18n` values ≤ 1000 chars. Unknown fields forbidden. The request discriminates on
`kind`.

**Validation through `DocumentService`**: both documents exist and both belong to the suggestion's
jurisdiction scope (equal jurisdiction, matching the unique constraint
`uq_requirement_parent_required_jurisdiction`). New read-only method
`DocumentService.get_document_jurisdiction(document_id) -> UUID | None`. Missing document → 422
(`UnknownDocumentError`); different jurisdiction → 422.

**Cycles are allowed to be suggested but flagged**: a direct cycle (required already requires parent) is
rejected with 422 `CycleError` because a dependency tree must stay acyclic; longer cycles are a seam.

**Duplicates**: an existing `document_requirement` for the same (parent, required, jurisdiction), or a
pending edge suggestion for the same triple → 409 with conflicts. Pending edge uniqueness gets a partial
unique index on `(jurisdiction_id, (payload->>'parent_document_id'), (payload->>'required_document_id'))
WHERE kind = 'new_requirement' AND status = 'pending'` in a small additive migration.

**`normalized_url` stays null** for this kind; `source_url` is still required for crawlers.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/suggestions/handlers.py` | `KindHandler`, `NewDocumentHandler`, `NewRequirementHandler`, `KIND_HANDLERS` |
| `apps/api/app/features/suggestions/service.py` | Delegates to the table |
| `apps/api/app/schema/suggestion/payload.py`, `create.py` | Payload and union |
| `apps/api/app/features/documents/service.py`, `repository.py` | `get_document_jurisdiction`, `requirement_exists`, `requires_directly` |
| `apps/api/alembic/versions/<yyyymmdd>_suggestion_pending_edge_unique.py` | Partial unique index |
| `apps/api/tests/test_suggestion_requirement_kind.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `refactor · all chapter 3–7 suggestion tests pass unchanged after the handler extraction` | Regression gate, first commit |
| `POST /suggestions · creates a pending requirement suggestion` | 201, kind |
| `POST /suggestions · rejects parent equal to required` | 422 |
| `POST /suggestions · rejects an unknown parent or required document` | 422 |
| `POST /suggestions · rejects documents from different jurisdictions` | 422 |
| `POST /suggestions · rejects a direct cycle` | 422 `CycleError` |
| `POST /suggestions · an existing requirement conflicts` | 409, conflict type `document_requirement` |
| `POST /suggestions · a pending identical edge conflicts` | 409, type `suggestion` |
| `POST /suggestions · an approved earlier edge suggestion does not block` | Negative pair |
| `POST /suggestions · two identical pending edges are rejected by the database` | Partial index |
| `POST /suggestions · a payload of the wrong shape for its kind gets 422` | Discriminator |
| `KIND_HANDLERS · has an entry for every SuggestionKind` | Guards future enum additions |

## Green

1. Extract `NewDocumentHandler`; test 1 (refactor commit, no behaviour change).
2. Payload and union; tests 2, 3, 11.
3. Existence and jurisdiction checks; tests 4, 5.
4. Cycle and duplicate rules, migration; tests 6–10.
5. Table completeness test; test 12.

## Refactor gate

- Handlers ≤ ~50 LOC each; `SuggestionService` keeps only orchestration and drops below ~80 LOC.
- No `if kind ==` remains anywhere in the suggestions feature (grep in the PR description).
- Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestion_requirement_kind.py tests/test_suggestions_submit.py tests/test_suggestion_duplicates.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

Promotion of edges (voting suite chapter 7), longer cycle detection, edge removal suggestions.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-requirement-kind
```

```text
refactor(api): move new-document rules into a kind handler table

test(api): describe requirement-edge suggestions and their duplicates

feat(api): add the new_requirement suggestion kind
```
