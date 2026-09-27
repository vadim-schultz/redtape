---
name: Auth — Gaps and decisions
overview: "Settled decisions and open seams for Supabase JWT authentication, roles and machine API keys."
isProject: false
---

# Auth — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

### D1 — Supabase Auth, verified by the API

The browser signs in with Supabase; the Litestar API only **verifies** tokens and never sees passwords or
issues them. Rejected: self-hosted sessions in Litestar (we would own password storage, resets and
email delivery) and third-party OIDC only (excludes people without those accounts).

### D2 — Asymmetric signing keys via JWKS

The verifier fetches the project's JWKS and checks the signature with the key matching the token's `kid`,
using PyJWT's `PyJWKClient` (sync, matches the sync API; key cache on). Rejected: the legacy shared HS256
secret (a leaked API secret would mint valid tokens for anyone). Pin the accepted algorithms to the JWKS
key types (`RS256`, `ES256`); never accept `none` or `HS*`.

### D3 — Roles live in our database

`app_user.role` is authoritative. Claims such as `role` in the JWT are Supabase's own (`authenticated`) and
unrelated. A moderator is promoted with a script (`scripts/set_user_role.py <email> moderator`), no UI.

### D4 — Users are mirrored lazily

The first authenticated request upserts `app_user(id=sub)`. No Supabase webhook, no background sync. Email
changes are refreshed on the same upsert.

### D5 — Dependencies, not global middleware

Auth is expressed as Litestar dependencies and guards on the routes that need them. Read endpoints stay
public and untouched. Rejected: a global authentication middleware (would need an allow-list of public
routes and hides which routes are protected).

### D6 — Magic link first

The first login method is an email magic link (`signInWithOtp`). No password fields exist in the UI; the
existing `auth.password` translation key is removed by chapter 10.

### D7 — API keys are hashed and shown once

Keys are 32 random bytes, URL-safe base64, prefixed `rt_`. Only the SHA-256 hex digest is stored (keys are
high-entropy, so a slow hash adds nothing). The plaintext is printed once by the issuing script. Revocation
sets `revoked_at`; nothing is deleted.

### D8 — Machine principals cannot vote or moderate

`MachinePrincipal` passes `require_machine` only. Human-only routes depend on `current_user`, so a crawler
key is rejected there with 401 by construction.

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Rate limiting on authenticated writes | None | Before [suggestion-interface chapter 5](../suggestion-interface/chapters/05-human-submit-endpoint.md) ships publicly |
| Email domain allow/deny and disposable-address blocking | None | First observed abuse |
| Account deletion and data export | None | `security-privacy-gdpr` strand |
| Key rotation policy for crawlers | Manual: issue new, revoke old | More than one crawler in production |
| Token in `localStorage` (`supabase-js` default) | Accepted for now | Any stored-XSS finding; then move to cookie-based sessions |
| Supabase project ownership and environments | One project | Separate staging environment |
