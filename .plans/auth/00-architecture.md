---
name: Auth — Architecture
overview: "Human login through Supabase Auth (email magic link), JWT verification in the Litestar API, a local app_user table with roles, hashed API keys for machine clients such as crawlers, and the web session, login UI and route guard."
isProject: false
---

# Auth — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Why

The API is read-only today: no POST endpoint, no user, no guard (verified in
[main.py](../../apps/api/app/main.py); CORS already allows credentials and write methods). The suggestion,
voting and crawler suites need to know **who** writes: people who submit and vote, moderators who decide,
and crawlers that submit at volume. The roadmap already chose Supabase Auth
([02-incremental-mvp-roadmap.md](../../docs/planning/02-incremental-mvp-roadmap.md), Wave 6); this suite
turns that into shippable chapters and adds the machine-client path the roadmap does not cover.

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **User** | A human with a Supabase account, mirrored as a row in `app_user` on first authenticated request. |
| **Role** | `user`, `moderator` or `admin`, stored in `app_user.role`. Never read from the JWT (D3). |
| **API key** | A secret issued to a machine client (a crawler). Only its SHA-256 hash is stored (D7). |
| **Principal** | Whoever made the request: a `UserPrincipal` or a `MachinePrincipal`. Both expose `kind`, `id`. |

## 3. Request flow

```
Browser ──magic link──► Supabase Auth ──JWT (access token)──► Browser
Browser ── Authorization: Bearer <JWT> ──► Cloudflare Worker ──► Litestar API
Crawler ── X-API-Key: <secret> ───────────────────────────────► Litestar API

Litestar dependency chain:
  bearer/api-key header ─► JwtVerifier | ApiKeyService ─► Principal ─► guards (role) ─► handler
```

The Worker proxy forwards all headers except `host` and `origin`
([proxyApi.ts](../../apps/web/src/worker/proxyApi.ts)); CORS uses `allow_headers=["*"]`
([cors.py](../../apps/api/app/middleware/cors.py)). No proxy or CORS change is needed for
`Authorization` or `X-API-Key`; chapter 9 locks this with a test rather than assuming it.

## 4. Backend layout

New feature slice `apps/api/app/features/auth/`, same file set as `documents`:

| File | Responsibility |
| --- | --- |
| `jwt.py` | `JwtVerifier`: verifies signature (JWKS), `iss`, `aud`, `exp`; returns `TokenClaims`. No database. |
| `repository.py` | `UserRepository`, `ApiKeyRepository`: SQLAlchemy queries only. |
| `service.py` | `UserService` (upsert on first sight, role lookup), `ApiKeyService` (issue, hash, verify, revoke). |
| `dependencies.py` | `provide_principal`, `provide_current_user`, `provide_optional_user`, service providers. |
| `guards.py` | `require_role(min_role)`, `require_machine`. |
| `controller.py`, `router.py` | `GET /api/v1/me`. |

Models `app_user`, `api_key` live in `apps/api/app/models/`; read schemas in `apps/api/app/schema/auth/`.
Layering follows the `tdd-workflow` rule: repositories talk to the session, services to repositories,
controllers compose services. Other features get the caller through the `current_user` dependency and never
touch `UserRepository`.

## 5. Data model

**`app_user`** — `id` UUID primary key (equals the Supabase `sub`, not generated), `email` String(320)
unique, `display_name` String(120) nullable, `role` native enum `user_role` (`user`, `moderator`, `admin`)
default `user`, `created_at`, `last_seen_at`.

**`api_key`** — `id` UUID, `name` String(120) (e.g. `crawler-prod`), `key_hash` String(64) unique (hex
SHA-256), `key_prefix` String(8) (first characters, shown in listings), `created_at`, `revoked_at` nullable,
`last_used_at` nullable.

## 6. API contract

| Route | Auth | Response |
| --- | --- | --- |
| `GET /api/v1/me` | Bearer | `{id, email, display_name, role}`; 401 without or with an invalid token |

Errors: **401** `{"status_code":401,"detail":"…"}` for missing, malformed, expired or wrongly signed
credentials; **403** for a valid principal with insufficient role. Both use Litestar's default error shape.

## 7. Web

`apps/web/src/features/auth/` holds `services/authGateway.ts` (the only file importing `@supabase/supabase-js`),
`contexts/AuthContext.tsx`, `containers/LoginPage.tsx`, `components/RequireAuth.tsx`. `apiRequest` gains an
optional `accessToken`; `useApi` supplies it from the context. Tests use a hand-written fake of
`authGateway` (own interface), not a mock of the Supabase library.

## 8. Configuration

| Variable | Where | Meaning |
| --- | --- | --- |
| `SUPABASE_JWKS_URL` | API | `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` |
| `SUPABASE_JWT_ISSUER` | API | `https://<ref>.supabase.co/auth/v1` |
| `SUPABASE_JWT_AUDIENCE` | API | `authenticated` |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | Web build | Public client config; the anon key is designed to be public |

`apps/api/.env.example` already lists `SUPABASE_URL` and keys as "later waves" that `Settings` ignores;
chapter 1 replaces them with the fields above.

## 9. Out of scope

Password login, OAuth providers, account deletion and GDPR export (strand `security-privacy-gdpr`), MFA,
session cookies, refresh-token handling beyond what `supabase-js` does, rate limiting, an admin UI for
roles and keys (scripts only), the mobile app.
