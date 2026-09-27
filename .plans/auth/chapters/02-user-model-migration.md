---
name: "Chapter 2 — User model and migration"
overview: "app_user table with the Supabase subject as primary key, unique email and a user_role enum, plus the SQLAlchemy model and a reversible migration."
todos:
  - id: model
    content: "AppUser model and UserRole enum, exported from app.models"
    status: pending
  - id: migration
    content: "Alembic revision chained off 20260625_taxonomy"
    status: pending
isProject: false
---

# Chapter 2 — User model and migration

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/auth-user-model` · **Status:** planned

**Depends on:** [ci-foundation 1–2](../../ci-foundation/01-rollout.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A place to store users, with the shape every later suite references (`suggestion.submitted_by_user_id`,
`suggestion_vote.user_id`).

## Design decisions

**Primary key is the Supabase `sub`.** `id` is a UUID with no default, so a row can only be created for an
identity Supabase vouched for, and joins never need a lookup by external id.

**Native enum `user_role`** (`user`, `moderator`, `admin`), matching the taxonomy migration's use of named
constraints. Downgrade drops the enum type after the table.

**Conventions copied from [20260625_taxonomy.py](../../../apps/api/alembic/versions/20260625_taxonomy.py):**
UUID keys, named constraints (`uq_app_user_email`), `server_default=func.now()` timestamps. Revision id
equals the filename stem: `<yyyymmdd>_app_user` (the day the chapter is implemented), chained off the
current single head (`20260625_taxonomy` at the time of writing; the migration check enforces one head).

**Email is unique, case-insensitively.** Stored lower-cased by the service in chapter 4; the unique index is
on `lower(email)` (`uq_app_user_email_lower`) so a differently-cased duplicate cannot slip in.

**No password, no token, no PII beyond email and optional display name** (GDPR seam in
[gaps](../gaps-and-decisions.md)).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/user.py` | `UserRole`, `AppUser` |
| `apps/api/app/models/__init__.py` | Export both |
| `apps/api/alembic/versions/<yyyymmdd>_app_user.py` | Create table, enum, unique index |
| `apps/api/tests/test_user_model.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `AppUser · persists with the supplied id and default role user` | Round trip through `db_session` |
| `AppUser · rejects a duplicate email` | `IntegrityError` |
| `AppUser · rejects an email differing only in case` | Negative pair of the previous test |
| `AppUser · rejects an unknown role value` | Enum constraint |
| `AppUser · created_at is set by the database` | Not null after flush |
| `migration · app_user table matches the model` | Inspector columns/constraints equal the model (also covered by `alembic check`) |

## Green

1. Model and enum; tests 1, 4, 5 (schema via `create_all`).
2. Unique index on lower(email); tests 2 and 3.
3. Migration; run the round trip.

## Refactor gate

One model per file (`user.py`), well under 100 LOC. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_user_model.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

Writing users (chapter 4), role changes (chapter 6), API keys (chapter 7).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-user-model
```

```text
test(api): describe app_user constraints and defaults

feat(api): add app_user model and migration
```
