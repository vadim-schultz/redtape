---
name: "Chapter 1 — Vote model and migration"
overview: "suggestion_vote table: one row per (suggestion, user), value constrained to +1/-1, cascade-deleted with either side, and a reversible migration."
todos:
  - id: model
    content: "SuggestionVote model"
    status: done
  - id: migration
    content: "Alembic revision with unique and check constraints"
    status: done
isProject: false
---

# Chapter 1 — Vote model and migration

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-model` · **Status:** implemented, PR open

**Depends on:** [suggestion-interface 1](../../suggestion-interface/chapters/01-suggestion-model-migration.md), auth [2](../../auth/chapters/02-user-model-migration.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Storage for one vote per user per suggestion (D1), enforced by the schema, not only by service logic.

## Design decisions

**`ck_suggestion_vote_value`** restricts `value` to `{-1, 1}` — a Postgres `CHECK` — so no code path can
store a "weight" or a zero vote by mistake (D8's simplicity is protected here too).

**`uq_suggestion_vote_user`** on (`suggestion_id`, `user_id`) is what makes "upsert, not append" (D1)
possible: the service in chapter 2 relies on `ON CONFLICT` against this exact constraint.

**Both foreign keys `ondelete=CASCADE`**: a deleted suggestion takes its votes with it (nothing to keep,
unlike evidence's design rationale, which is about the suggestion itself, not votes on it); a deleted user
(GDPR) takes their votes with it too — unlike `app_user` on suggestions, a vote has no meaning without its
voter, so cascade (not `SET NULL`) is correct here specifically.

**Conventions**: UUID key, named constraints, `server_default=func.now()`, matching
[20260625_taxonomy.py](../../../apps/api/alembic/versions/20260625_taxonomy.py). Revision
`<yyyymmdd>_suggestion_vote`, chained off the current single head.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/suggestion_vote.py`, `apps/api/app/models/__init__.py` | Model and export |
| `apps/api/alembic/versions/<yyyymmdd>_suggestion_vote.py` | Migration |
| `apps/api/tests/test_suggestion_vote_model.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `SuggestionVote · persists a valid vote` | Round trip |
| `SuggestionVote · rejects a value other than 1 or -1` | Check constraint |
| `SuggestionVote · rejects a second row for the same suggestion and user` | Unique constraint |
| `SuggestionVote · allows the same user to vote on a different suggestion` | Negative pair |
| `SuggestionVote · deleting the suggestion deletes its votes` | Cascade |
| `SuggestionVote · deleting the user deletes their votes` | Cascade |

## Green

1. Model; tests 1, 2.
2. Unique constraint; tests 3–4.
3. Cascades; tests 5–6.
4. Migration and round trip.

## Refactor gate

Model file ≤ ~60 LOC. Report the outcome.

**Outcome:** `app/models/suggestion_vote.py` is 32 LOC — one class, two module-level constraint-name
constants (`CK_VALUE`, `UQ_USER`), no nesting beyond the single class body. No further extraction needed.

## Progress

All 6 red tests pass against Postgres (`tests/test_suggestion_vote_model.py`); `alembic upgrade head` →
`downgrade -1` → `upgrade head` round-trips cleanly and `alembic check` reports no drift against the model.
`./ci.sh` (lint, format, mypy, migrations, pytest, web) is green.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestion_vote_model.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

Casting a vote through code (chapter 2), tallying (chapter 4).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-model
```

```text
test(api): describe vote constraints and cascades

feat(api): add suggestion_vote model and migration
```
