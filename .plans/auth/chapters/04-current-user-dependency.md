---
name: "Chapter 4 — Current-user dependency"
overview: "A current_user dependency that turns the Authorization bearer header into an AppUser (upserted on first sight), and an optional variant; the first Litestar wiring of the verifier."
todos:
  - id: repo
    content: "UserRepository get and upsert"
    status: pending
  - id: service
    content: "UserService.resolve(claims)"
    status: pending
  - id: dep
    content: "provide_current_user and provide_optional_user"
    status: pending
isProject: false
---

# Chapter 4 — Current-user dependency

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/auth-current-user` · **Status:** planned

**Depends on:** [2](02-user-model-migration.md), [3](03-jwt-verifier.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3–4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Any handler can declare `current_user: AppUser` and receive the authenticated user, or `401`. A second
provider yields `AppUser | None` for routes that behave differently when logged in (for example a `my_vote`
field on public reads in the voting suite).

## Design decisions

**Layering (tdd-workflow).** `UserRepository` (session queries) → `UserService.resolve(claims)` (upsert
and refresh email/name/`last_seen_at`) → dependency provider (HTTP concerns: read the header, call the
verifier, map `AuthError` to `NotAuthorizedException`). The provider is the only piece that knows about
`Request`.

**Upsert on first sight** (D4): insert `app_user(id=sub, email=lower(email))` on conflict update email,
`display_name`, `last_seen_at`. One statement, race-safe (`ON CONFLICT (id) DO UPDATE`).

**Header parsing**: exactly `Authorization: Bearer <token>`. Wrong scheme, empty token and extra segments
are `malformed`. The response body is `{"detail": "Not authenticated"}` for every failure; the reason code
goes to the log, not to the client.

**Auth disabled** (chapter 1): `provide_current_user` raises 401 without touching the verifier when
`settings.auth_enabled` is false; `provide_optional_user` returns `None`. So today's deployment is unchanged.

**Verifier wiring.** `provide_jwt_verifier` builds one `JwtVerifier` per process (module-level cache) from
settings, and the tests override it through Litestar's `dependencies` with a verifier using a local key.
No network in tests.

**Registration.** The providers are exported in `features/auth/dependencies.py` as `router_dependencies`
(same convention as documents/taxonomy). Feature routers that need them merge that dict; nothing is added
to the global app.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/auth/repository.py` | `UserRepository.upsert(claims)`, `get(id)` |
| `apps/api/app/features/auth/service.py` | `UserService.resolve(claims) -> AppUser` |
| `apps/api/app/features/auth/dependencies.py` | Providers and `router_dependencies` |
| `apps/api/tests/test_current_user.py` | Tests below (Litestar `TestClient` on a tiny test router) |

## Red tests

| Test | Asserts |
| --- | --- |
| `UserRepository · upsert inserts a new user with role user` | Row exists |
| `UserRepository · upsert refreshes email and last_seen_at for an existing user` | Same id, no second row |
| `UserService · resolve lower-cases the email` | Stored value |
| `current_user · valid bearer token returns the user` | 200 on a probe route |
| `current_user · missing header returns 401` | Negative |
| `current_user · wrong scheme returns 401` | `Basic abc` |
| `current_user · invalid token returns 401 without a reason in the body` | No leakage |
| `current_user · auth disabled returns 401` | Even for a "valid-looking" token |
| `optional_user · missing header returns None` | 200, anonymous |
| `optional_user · invalid token returns 401, not anonymous` | A bad token is never silently downgraded |

## Green

1. Repository upsert; tests 1–2.
2. Service; test 3.
3. Provider for the happy path with an overridden verifier; test 4.
4. Failure mapping; tests 5–8.
5. Optional variant; tests 9–10.

## Refactor gate

- Header parsing is a named function (`_bearer_token(request)`); providers ≤ ~5 LOC.
- Upsert is one repository method; the service does not build SQL.
- Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_current_user.py
cd ../.. && ./ci.sh
```

## Out of scope

Roles (chapter 6), `/me` (chapter 5), API keys (chapters 7–8), applying the dependency to feature routes.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-current-user
```

```text
test(api): describe current-user resolution from bearer tokens

feat(api): add current_user and optional_user dependencies
```
