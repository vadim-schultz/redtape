# Auth setup runbook

How to stand up Supabase Auth for `redtape`, promote the first moderator, and issue or revoke crawler API
keys. Design and decisions: [`.plans/auth/00-architecture.md`](../../.plans/auth/00-architecture.md) and
[`docs/planning/directions/backend-api/03-auth-and-roles.md`](../planning/directions/backend-api/03-auth-and-roles.md).

Every step below is optional: with no Supabase variables set, the API answers 401 on protected routes and
the web app shows no login entry — nothing breaks by leaving auth off (rollout invariant 2).

## 1. Create the Supabase project

Use the same Supabase project already used for `DATABASE_URL` (one project for Postgres + Auth, per
[01-stack-and-free-tier.md](../planning/01-stack-and-free-tier.md)) — do not create a second one.

## 2. Enable email OTP

Supabase dashboard → **Authentication → Providers → Email**: enable the provider, leave **Confirm email**
on. No password field is used anywhere in this app (D6) — only `signInWithOtp` magic links.

## 3. Set the redirect URLs

Supabase dashboard → **Authentication → URL Configuration → Redirect URLs**. The web app sends
`emailRedirectTo: <origin>/login` ([`supabaseAuthGateway.ts`](../../apps/web/src/features/auth/services/supabaseAuthGateway.ts)),
so add one entry per origin that will ever request a magic link:

- Local: `http://localhost:5173/login`
- Production: `https://redtape-web.vadim-schultz.workers.dev/login` (see
  [deployment-checklist.md](deployment-checklist.md) for the current live origin)
- Any future preview deployment's origin, added as it's created — Supabase's redirect list accepts
  wildcard patterns (e.g. `https://*.redtape-web.pages.dev/login`) if previews start using a shared
  subdomain pattern.

A login attempt from an origin not on this list fails at Supabase, not at the API.

## 4. Set the API variables

`apps/api/.env.example` documents these; set the real values in Render (or your local `.env`), never commit
them:

| Variable | Value |
| --- | --- |
| `SUPABASE_JWKS_URL` | `https://<project_ref>.supabase.co/auth/v1/.well-known/jwks.json` |
| `SUPABASE_JWT_ISSUER` | `https://<project_ref>.supabase.co/auth/v1` |
| `SUPABASE_JWT_AUDIENCE` | `authenticated` (Supabase's default; only override if you changed it) |

`Settings.auth_enabled` is true only once both the JWKS URL and issuer are set
([`config.py`](../../apps/api/app/config.py)).

## 5. Set the web variables

`apps/web/.env.example` documents these; set the real values as Cloudflare Workers Build variables (see
[deployment-checklist.md](deployment-checklist.md) for why dashboard-only variables don't survive a
git-triggered build):

| Variable | Value |
| --- | --- |
| `VITE_SUPABASE_URL` | `https://<project_ref>.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | The project's anon key — this key is designed to be public |

With both unset, the auth gateway reports `unconfigured` and the app behaves exactly as it did before
chapter 9: no account menu item, no protected routes.

## 6. Promote the first moderator

A user must sign in at least once (so their `app_user` row exists) before they can be promoted — there is
no bootstrap admin. From `apps/api`:

```bash
python -m scripts.set_user_role <email> moderator
```

Roles are `user`, `moderator` or `admin`. The script is idempotent and exits non-zero for an unknown email
or role name. There is no HTTP endpoint or UI for this by design (D3) — only an operator with database
access can change roles.

## 7. Issue and revoke crawler keys

Machine clients (crawlers) authenticate with `X-API-Key` instead of a Supabase session. From `apps/api`:

```bash
# Issue — the plaintext key is printed exactly once and is never stored or logged
python -m scripts.issue_api_key --name crawler-prod

# Revoke — by the key_prefix shown when the key was issued (or in any listing)
python -m scripts.issue_api_key --revoke <key_prefix>
```

Only the SHA-256 hash of the key is stored (D7); if the plaintext is lost, revoke it and issue a new one —
there is no way to recover or re-display it. A revoked key's requests fail with 401.

A machine principal can never pass `require_role` — human-only routes (voting, moderation) reject crawler
keys by construction (D8), so a crawler key only needs the scopes its own submission routes require.

## 8. Rotate

There is no automatic rotation policy yet (open seam — see
[gaps-and-decisions.md](../../.plans/auth/gaps-and-decisions.md)). To rotate a crawler key by hand: issue
the replacement first, update the crawler's configured secret, confirm it's being used (`last_used_at`
advances), then revoke the old prefix. Rotating a moderator or admin's access means changing their role with
`set_user_role.py`; their Supabase login itself is managed in the Supabase dashboard, not by this repo.
