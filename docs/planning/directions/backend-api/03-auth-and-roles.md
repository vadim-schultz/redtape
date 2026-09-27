# Chapter: Auth and roles (shipped)

Full design, chapter-by-chapter history and open seams live in [`.plans/auth/`](../../../../.plans/auth/00-architecture.md);
this page is the strand-level summary the [backend-api README](README.md) pointed at as TBD.

## Goal

The API needs to know **who** is writing: people who sign in with Supabase, and machine clients (crawlers)
that authenticate with a key. Read endpoints stay public and unchanged (D5); this chapter adds the
principal, role and machine-key plumbing that later suites (suggestions, voting, crawlers) build on.

## Principals

| Kind | Issued by | Carries |
| --- | --- | --- |
| `UserPrincipal` | Supabase Auth (email magic link), verified by the API via JWT | `id` (= Supabase `sub`), role from `app_user` |
| `MachinePrincipal` | `scripts/issue_api_key.py`, an API key in `X-API-Key` | `id` (the `api_key` row) |

Both expose `kind` and `id`; `require_machine` rejects a `UserPrincipal` and vice versa, so a crawler key on
a human-only route is a 401 by construction (D8).

## Roles

`app_user.role` is `user`, `moderator` or `admin`, stored in our database and never read from the JWT (D3—
Supabase's own `role` claim is `authenticated` and unrelated). Ranks are `user=0 < moderator=1 < admin=2`;
`require_role(min_role)` is a Litestar guard that lets equal-or-higher ranks through. There is no
role-changing endpoint: `scripts/set_user_role.py <email> <role>` promotes from the command line, the only
way today (see [auth-setup.md](../../../operations/auth-setup.md)).

## Verification flow

```
Browser ──magic link──► Supabase Auth ──JWT (access token)──► Browser
Browser ── Authorization: Bearer <JWT> ──► API
Crawler ── X-API-Key: <secret> ──────────► API
```

`JwtVerifier` fetches the project's JWKS and checks the signature against the key matching the token's
`kid`, plus `iss`, `aud` and `exp` (D2 — asymmetric keys only; `none` and `HS*` are never accepted). The
first authenticated request upserts `app_user(id=sub)` (D4 — no Supabase webhook). API keys are 32 random
bytes, URL-safe base64, prefixed `rt_`; only the SHA-256 hex digest is stored, and the plaintext is printed
once by the issuing script (D7).

Auth is expressed as Litestar dependencies and guards on the routes that need them, not global middleware
(D5), and is off — not broken — when `SUPABASE_JWKS_URL` / `SUPABASE_JWT_ISSUER` are unset: protected
routes 401 and reads behave as before any Supabase project exists (rollout invariant 2).

## Error shapes

Litestar's default error shape throughout:

- **401** `{"status_code":401,"detail":"…"}` — missing, malformed, expired or wrongly signed credentials, or
  no credentials at all.
- **403** `{"status_code":403,"detail":"Insufficient role"}` — a valid principal below the route's minimum
  role.

## Backend layout

Feature slice `apps/api/app/features/auth/` — `jwt.py` (`JwtVerifier`, no database), `repository.py`
(`UserRepository`, `ApiKeyRepository`), `service.py` (`UserService`, `ApiKeyService`), `dependencies.py`
(`provide_principal`, `provide_current_user`), `guards.py` (`require_role`, `require_machine`),
`controller.py` / `router.py` (`GET /api/v1/me`). Models `app_user` and `api_key` live in
`apps/api/app/models/`. Other features reach auth only through the `current_user` dependency, never through
`UserRepository` directly (tdd-workflow layering).

## Out of scope

Password login, OAuth providers, MFA, rate limiting, an admin UI for roles and keys, account deletion and
GDPR export (`security-privacy-gdpr` strand). Full list and forcing conditions:
[`.plans/auth/gaps-and-decisions.md`](../../../../.plans/auth/gaps-and-decisions.md).
