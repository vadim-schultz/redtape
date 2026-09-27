---
name: "Chapter 6 — Role guards"
overview: "A require_role guard ordering user < moderator < admin, and a script to promote a user, so moderator-only routes in later suites can be expressed in one line."
todos:
  - id: guard
    content: "require_role(min_role) Litestar guard"
    status: completed
  - id: script
    content: "scripts/set_user_role.py"
    status: completed
isProject: false
---

# Chapter 6 — Role guards

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/auth-role-guards` · **Status:** done

**Depends on:** [4](04-current-user-dependency.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`guards=[require_role(UserRole.moderator)]` on a route returns 401 for anonymous callers, 403 for a user
below the required role, and lets moderators and admins through. An operator can promote an account from
the command line (D3).

## Design decisions

**Ordered roles.** `UserRole` gets a rank (`user=0, moderator=1, admin=2`) through a module-level mapping,
not by relying on enum declaration order. `require_role(min_role)` compares ranks; higher roles pass.

**Guard reads the dependency, not the token.** The guard resolves the current user through the same
`provide_current_user` (Litestar guards receive the connection; the guard calls a small
`user_from_connection` helper shared with the dependency), so role checks always see the database role.

**401 vs 403.** No credentials → 401 (from the dependency); credentials but too low → 403 with
`{"detail": "Insufficient role"}`.

**Promotion script.** `apps/api/scripts/set_user_role.py <email> <role>` follows the seed-script style
([seed_taxonomy.py](../../../apps/api/scripts/seed_taxonomy.py)): a `main()` using `SessionLocal`, idempotent,
exits non-zero for an unknown email or role. The user must have logged in once (the row exists). Rejected:
role-changing HTTP endpoint (needs an admin bootstrap and UI; deferred, see seams).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/user.py` | `ROLE_RANK` mapping |
| `apps/api/app/features/auth/guards.py` | `require_role` |
| `apps/api/app/features/auth/service.py` | `set_role(email, role)` |
| `apps/api/scripts/set_user_role.py` | CLI wrapper |
| `apps/api/tests/test_role_guards.py`, `apps/api/tests/test_set_user_role.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `require_role · user role is forbidden on a moderator route` | 403 |
| `require_role · moderator passes a moderator route` | 200 |
| `require_role · admin passes a moderator route` | Higher rank allowed |
| `require_role · moderator is forbidden on an admin route` | 403 |
| `require_role · anonymous gets 401, not 403` | Ordering of failures |
| `UserService.set_role · updates the stored role` | Row changed |
| `UserService.set_role · unknown email raises` | Negative |
| `set_user_role script · rejects an unknown role name` | Non-zero exit, message lists valid roles |
| `set_user_role script · is idempotent` | Second run succeeds, no change |

## Green

1. `ROLE_RANK` and guard; tests 1–5 on a probe route.
2. Service method; tests 6–7.
3. Script; tests 8–9.

## Refactor gate

- `require_role` is a closure of ≈5 LOC returning the guard; the rank comparison is one function.
- Script `main()` only parses arguments and calls the service.
- Report the outcome.

✅ `require_role`'s guard body is 5 lines; rank comparison lives in its own `_role_allows` function, so the
closure never touches `ROLE_RANK` directly. `set_user_role.py`'s `main()` only builds the argument parser,
opens a session and calls `_set_role_or_exit`/`session.commit()`; role-name validation and its "valid
roles" message live in `UserService.set_role` (`UnknownRoleError`), not in the script, so `main()` never
branches on role validity itself.

One wrinkle not anticipated in the design: Litestar guards receive only the raw `ASGIConnection`, called
*before* the framework resolves any `Provide`-based dependencies (including `session`). So `require_role`
can't reuse the request's injected session the way `provide_current_user` does — it opens its own via
`SessionLocal()` for the single `user_from_connection` call and commits before returning. In production
this is a second, short-lived connection per guarded request (acceptable: the design doc already assumes
the row was committed by an earlier request); tests substitute a no-close wrapper around the fixture's
transactional session so guard reads stay inside the same rolled-back transaction as the rest of the test.
No AI/typesafe-ai judgment call here — role comparison is a deterministic rank lookup, not something to
delegate to a model.

## Verification

```bash
cd apps/api
python -m pytest tests/test_role_guards.py tests/test_set_user_role.py
cd ../.. && ./ci.sh
```

## Out of scope

Role UI, audit log of role changes (covered by the voting suite's event log for suggestion actions only).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-role-guards
```

```text
test(api): describe role ordering, 401 versus 403 and promotion

feat(api): add require_role guard and set_user_role script
```
