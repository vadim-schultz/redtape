---
name: "Chapter 5 — /me endpoint"
overview: "GET /api/v1/me returns the authenticated user's id, email, display name and role; the first protected route and the contract the web session calls after login."
todos:
  - id: schema
    content: "UserRead schema"
    status: completed
  - id: route
    content: "Auth controller and router registered in the app"
    status: completed
isProject: false
---

# Chapter 5 — /me endpoint

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/auth-me` · **Status:** done

**Depends on:** [4](04-current-user-dependency.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`GET /api/v1/me` → `{id, email, display_name, role}`. It is how the web app learns the local role
(moderators see extra UI) and proves the whole chain works end to end.

## Design decisions

**Own feature slice.** `router.py` (`/api/v1`, tag `auth`) merges `auth.dependencies.router_dependencies`;
`controller.py` has one handler with `sync_to_thread=True`, like the documents controller. The router is
added to `route_handlers` in [main.py](../../../apps/api/app/main.py).

**Response is a Pydantic read model** in `apps/api/app/schema/auth/read.py`, not the ORM object, so new
columns never leak by accident. No `created_at`, no internal flags.

**No caching headers**: the response is per-user; `Cache-Control: no-store` is set on the handler.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/schema/auth/read.py` | `UserRead` |
| `apps/api/app/features/auth/controller.py` | `MeController` |
| `apps/api/app/features/auth/router.py` | `auth_router` |
| `apps/api/app/main.py` | Register the router |
| `apps/api/tests/test_me_endpoint.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `GET /me · returns the current user's profile` | Shape and values |
| `GET /me · returns the role stored in the database, not the token's` | Role `moderator` in DB → response says moderator |
| `GET /me · first call creates the user row` | Row count 0 → 1 |
| `GET /me · second call does not create a duplicate` | Row count stays 1 |
| `GET /me · returns 401 without a token` | Negative |
| `GET /me · response is not cacheable` | `Cache-Control: no-store` |
| `GET /me · response omits fields outside the read model` | Exactly four keys |

## Green

1. Schema, controller, router; tests 1, 5.
2. Registration; tests 3–4.
3. Role and headers; tests 2, 6, 7.

## Refactor gate

Handler is `return UserRead.model_validate(current_user)` plus the header decorator argument; nothing to
extract. Report the outcome.

✅ No refactor needed, as predicted. `controller.py` is 16 LOC total: one `Controller` with one `get`
handler whose body is the single `model_validate` line; the `Cache-Control: no-store` requirement is
declared via the handler's `cache_control` argument rather than written into the body, so there was never
a second branch to dispatch on. No AI/typesafe-ai use here either — the endpoint returns exactly what's in
`app_user`, a deterministic projection, not a judgment call.

## Verification

```bash
cd apps/api
python -m pytest tests/test_me_endpoint.py
cd ../.. && ./ci.sh
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/me   # with Supabase configured
```

## Out of scope

Profile editing, avatar, listing users.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-me
```

```text
test(api): describe the me endpoint and its 401

feat(api): add GET /api/v1/me
```
