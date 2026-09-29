---
name: "Chapter 6 — Promote new_document"
overview: "transition_to approved for a new_document suggestion creates a real Document with the payload's title, description, URL and taxonomy tags, using the same slug the duplicate check already computed."
todos:
  - id: create
    content: "DocumentService.create_from_suggestion (first write method on a read-only service)"
    status: done
  - id: promoter
    content: "Kind-dispatched promotion inside transition_to"
    status: done
isProject: false
---

# Chapter 6 — Promote new_document

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-promote-document` · **Status:** implemented, PR open

**Depends on:** [5](05-status-transitions.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The moment a `new_document` suggestion is approved, a real `Document` exists — this is the whole point of
the program (crawlers and people grow the catalogue).

## Design decisions

**`DocumentService.create_from_suggestion(payload: NewDocumentPayload, jurisdiction_id, slug) ->
Document`** is documents' **first write method** (it has been read-only since Wave 1). It builds a
`Document` from the payload fields, resolves `domain_codes`/`situation_codes` to ids through
`TaxonomyService` (already a documents collaborator), and persists it. The slug is **passed in**, computed
once by the same `slugify` used for duplicate detection (suggestion-interface chapter 2/4) — never
recomputed, so promotion can never disagree with what the duplicate check already verified was free.

**Dispatch lives where kind dispatch already lives.** `transition_to`, on reaching `approved`, calls
`KIND_HANDLERS[suggestion.kind].promote(suggestion, session)` (suggestion-interface chapter 8's table gains
a `promote` method per handler); `NewDocumentHandler.promote` calls `document_service.create_from_suggestion`
and returns the created id. `NewRequirementHandler.promote` (chapter 7) raises `NotImplementedError` until
then — table-completeness test from chapter 8 already exists and will need updating in this chapter's PR
description (not a new test; noted for the implementer).

**Race with a second suggestion for the same slug approved concurrently**: prevented by the same duplicate
check re-run immediately before insert (`find_conflicts` again, inside the transition's transaction) — if
another suggestion won the race, promotion raises `PromotionConflictError` and the transition is aborted
(status stays `pending`, no partial state); this is a rare, explicitly tested path, not silently ignored.

**One transaction.** Status write and document creation happen in the same database transaction
(`provide_session`'s existing commit/rollback boundary already gives this "for free" — no explicit
transaction management is added, just care that nothing commits early).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/documents/service.py`, `repository.py` | `create_from_suggestion`, `add` |
| `apps/api/app/features/suggestions/handlers.py` | `NewDocumentHandler.promote` |
| `apps/api/app/features/suggestions/service.py` | `transition_to` calls `promote` on approval |
| `apps/api/tests/test_promote_new_document.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `promote · approving a new_document suggestion creates a Document with its title, description and URL` | Field mapping |
| `promote · resolves domain and situation codes onto the created document` | Tag associations |
| `promote · uses the slug computed at submission time, not recomputed` | Same value, no drift possible |
| `promote · a second suggestion racing for the same slug fails without corrupting either row` | `PromotionConflictError`, status stays pending |
| `promote · the created document is retrievable through the existing documents endpoint` | End-to-end read |
| `promote · approving twice is prevented by AlreadyDecidedError, not a duplicate document` | Regression from chapter 5 |
| `promote · a rejected suggestion never creates a document` | Negative |

## Green

1. `create_from_suggestion`; test 1.
2. Taxonomy resolution; test 2.
3. Slug reuse; test 3.
4. Handler wiring into `transition_to`; tests 5–7.
5. Race guard; test 4.

## Refactor gate

`create_from_suggestion` composes named steps (`_resolve_tags`, `_build_document`) each ≈5 LOC; if
`transition_to` exceeds ~15 LOC with promotion added, extract a `SuggestionTransition` handler object now
(the size trigger flagged in chapter 5). Report the outcome.

**Outcome:** `create_from_suggestion` is 4 lines (`_resolve_tags`, `_build_document`, `_repo.add`), each
named step ≈3–5 LOC as scoped. `transition_to` gained one line (`self._handlers[suggestion.kind].promote(suggestion)`,
called on `approved` *before* the status write, not after) and is 8 LOC total — well under the 15 LOC
trigger, so no `SuggestionTransition` extraction was needed. Promoting before the status assignment also
means the race guard needs no rollback reasoning: on `PromotionConflictError` the suggestion's in-memory
`status` was never touched, so "no partial state" is structural, not just transactional.

One deviation from the design note: `KindHandler.promote` takes only `suggestion`, not `(suggestion,
session)` — the handler already holds `documents`/`taxonomy`/`suggestions` collaborators from its
constructor (the same pattern `validate`/`conflicts` already use), so a session parameter would have been
unused. The suggestion-interface chapter 8 table-completeness test (`assert set(KIND_HANDLERS) ==
set(SuggestionKind)`) needed no changes — it asserts kind coverage, not per-handler method surface, and
`KindHandler` is a structural `Protocol` so adding `promote` to it isn't enforced at runtime.

Two pre-existing fixtures (`test_suggestion_transitions.py`, `test_vote_service.py`) built a `NEW_DOCUMENT`
suggestion with an empty payload; now that `approved` actually promotes, they needed a minimal valid
payload to keep testing status-transition mechanics instead of failing on `NewDocumentPayload` validation.

## Verification

```bash
cd apps/api
python -m pytest tests/test_promote_new_document.py tests/test_documents_filter.py
cd ../.. && ./ci.sh
```

## Out of scope

Promoting `new_requirement` (chapter 7), event logging of the promotion (chapter 8).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-promote-document
```

```text
test(api): describe promoting an approved new_document suggestion

feat(api): create a Document when a new_document suggestion is approved
```
