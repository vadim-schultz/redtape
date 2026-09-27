---
name: "Chapter 1 — Suggestion model and migration"
overview: "suggestion table with kind, status and source enums, submitter foreign keys constrained to match the source, an idempotency uniqueness rule, and a reversible migration."
todos:
  - id: model
    content: "Suggestion model and three enums, exported from app.models"
    status: pending
  - id: migration
    content: "Alembic revision with enums, table, constraints, indexes"
    status: pending
isProject: false
---

# Chapter 1 — Suggestion model and migration

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-model` · **Status:** planned

**Depends on:** auth [2](../../auth/chapters/02-user-model-migration.md) and [7](../../auth/chapters/07-api-key-model-and-hashing.md) (foreign keys) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Storage for suggestions with the invariants that must hold regardless of which code writes them.

## Design decisions

**Database enforces the source/submitter rule** with a check constraint
`ck_suggestion_submitter_matches_source` instead of relying on the service alone: exactly the user column is
set for `human`, exactly the key column for `crawler`. A later bug cannot create an orphan or double-owned row.

**`ondelete=SET NULL`** on both submitter foreign keys keeps a suggestion when an account or key is removed
(GDPR deletion must not erase moderation history). The check constraint would then fail on the nulling
update, so it is written as `(source_type = 'human' AND submitted_by_api_key_id IS NULL) OR
(source_type = 'crawler' AND submitted_by_user_id IS NULL)`: at most one is set, and the matching one may be
null after deletion.

**Idempotency**: `uq_suggestion_key_idempotency` on (`submitted_by_api_key_id`, `idempotency_key`);
Postgres treats nulls as distinct, so human rows and keyless rows never collide.

**Indexes**: `jurisdiction_id`, (`status`, `created_at`), `normalized_url`.

**Conventions**: UUID key, named constraints, `server_default` timestamps and JSONB defaults, as in
[20260625_taxonomy.py](../../../apps/api/alembic/versions/20260625_taxonomy.py). Enums are created and
dropped explicitly in the migration. Revision `<yyyymmdd>_suggestion`, chained off the single head.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/suggestion.py`, `apps/api/app/models/__init__.py` | Model, `SuggestionKind`, `SuggestionStatus`, `SuggestionSource` |
| `apps/api/alembic/versions/<yyyymmdd>_suggestion.py` | Migration |
| `apps/api/tests/test_suggestion_model.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `Suggestion · persists with defaults status pending and generated id` | Round trip |
| `Suggestion · human suggestion requires no API key` | Human + user id accepted |
| `Suggestion · human suggestion with an API key is rejected` | Check constraint |
| `Suggestion · crawler suggestion with a user id is rejected` | Check constraint |
| `Suggestion · deleting the submitting user keeps the suggestion` | `submitted_by_user_id` becomes null, row survives |
| `Suggestion · same API key and idempotency key twice is rejected` | Unique violation |
| `Suggestion · same idempotency key from two different API keys is allowed` | Scoped uniqueness |
| `Suggestion · two human suggestions without keys do not collide` | Nulls distinct |
| `Suggestion · unknown kind or status is rejected` | Enum |
| `Suggestion · payload defaults to an empty object` | JSONB default |

## Green

1. Model and enums; tests 1, 9, 10.
2. Check constraint; tests 2–4.
3. FK behaviour; test 5.
4. Idempotency uniqueness; tests 6–8.
5. Migration and round trip.

## Refactor gate

Model file ≤ ~100 LOC; enums in the same file; constraint names as module constants. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestion_model.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

Payload validation (chapter 2), any endpoint, evidence and vote tables (other suites).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-model
```

```text
test(api): describe suggestion constraints, defaults and idempotency

feat(api): add suggestion model and migration
```
