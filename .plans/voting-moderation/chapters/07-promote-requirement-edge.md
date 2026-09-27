---
name: "Chapter 7 — Promote requirement edge"
overview: "transition_to approved for a new_requirement suggestion creates a real DocumentRequirement edge, completing the kind-handler promotion table."
todos:
  - id: create
    content: "DocumentService.create_requirement_from_suggestion"
    status: pending
  - id: handler
    content: "NewRequirementHandler.promote"
    status: pending
isProject: false
---

# Chapter 7 — Promote requirement edge

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-promote-requirement` · **Status:** planned

**Depends on:** [5](05-status-transitions.md), suggestion-interface [8](../../suggestion-interface/chapters/08-requirement-edge-kind.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The dependency graph grows the same way documents do: an approved `new_requirement` suggestion becomes a
real `DocumentRequirement` row.

## Design decisions

**Mirrors chapter 6 exactly.** `DocumentService.create_requirement_from_suggestion(parent_id, required_id,
jurisdiction_id, notes_i18n) -> DocumentRequirement`, `source="community"` (distinct from the seeded
`"canonical"` default already on the model — this is the first non-canonical writer, so the distinction the
column already had becomes meaningful). `NewRequirementHandler.promote` calls it and completes the
`KIND_HANDLERS` table (the completeness test from suggestion-interface chapter 8 now passes with both
handlers implemented, replacing its `NotImplementedError` placeholder from chapter 6).

**Re-validated at promotion time, not just at submission time**: both documents still exist and still share
the jurisdiction (a document could theoretically be removed between submission and approval — no delete
path exists yet, but this guard costs one query and removes a latent assumption); a direct-cycle re-check
also re-runs (mirrors chapter 6's slug-race guard, same shape: `PromotionConflictError` on failure, no state
change).

**No duplicate edge**: the promotion re-checks `requirement_exists` (suggestion-interface chapter 8) right
before insert, same reasoning as chapter 6's slug race.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/documents/service.py`, `repository.py` | `create_requirement_from_suggestion` |
| `apps/api/app/features/suggestions/handlers.py` | `NewRequirementHandler.promote` |
| `apps/api/tests/test_promote_requirement_edge.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `promote · approving a new_requirement suggestion creates a DocumentRequirement` | Row exists, `source == "community"` |
| `promote · the created edge appears in the parent document's requirements` | End-to-end read via documents detail |
| `promote · re-validates both documents still exist at promotion time` | Simulated deletion between submit and approve → `PromotionConflictError` |
| `promote · re-validates the jurisdiction match at promotion time` | Same |
| `promote · rejects promoting a duplicate edge that appeared after submission` | `PromotionConflictError` |
| `KIND_HANDLERS · both kinds now promote without NotImplementedError` | Completes chapter 8's table test |

## Green

1. `create_requirement_from_suggestion`; test 1.
2. Handler wiring; tests 2, 6.
3. Re-validation guards; tests 3–5.

## Refactor gate

`create_requirement_from_suggestion` mirrors `create_from_suggestion`'s shape; if the duplication between
the two exceeds the rule of three (a third promotable kind would make it obvious), extract a shared
`_promote_common` step — not yet, with only two. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_promote_requirement_edge.py tests/test_document_jurisdiction_path.py
cd ../.. && ./ci.sh
```

## Out of scope

Event logging (chapter 8), moderator override (chapter 9).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-promote-requirement
```

```text
test(api): describe promoting an approved requirement-edge suggestion

feat(api): create a DocumentRequirement when a new_requirement suggestion is approved
```
