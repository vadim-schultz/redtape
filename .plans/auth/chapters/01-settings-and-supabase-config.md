---
name: "Chapter 1 — Settings and Supabase config"
overview: "Settings gains the JWKS URL, issuer and audience, an auth_enabled property, and .env.example documents them; with nothing configured, auth is simply off."
todos:
  - id: settings
    content: "Settings fields and auth_enabled"
    status: completed
  - id: env
    content: ".env.example replaces the unused Supabase placeholders"
    status: completed
isProject: false
---

# Chapter 1 — Settings and Supabase config

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/auth-settings` · **Status:** done

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Later chapters read `settings.supabase_jwks_url`, `supabase_jwt_issuer`, `supabase_jwt_audience`. An
`auth_enabled` property is true only when JWKS URL and issuer are both set, so every environment without
Supabase (local dev, CI, current production) behaves as today.

## Design decisions

**Follow the existing pattern.** [config.py](../../../apps/api/app/config.py) is a pydantic-settings class
with a module-level `settings`; new fields are plain optional strings, not a nested model.

**Off by default, not broken by default.** Missing values do not raise at import; later chapters make
protected routes answer 401 when `auth_enabled` is false (chapter 4). Audience defaults to `authenticated`.

**`.env.example` cleanup.** The current `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
placeholders are never read. The service-role key is removed on purpose: the API needs no privileged
Supabase access under D1, and leaving the line invites pasting a secret that gives full database bypass.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/config.py` | Three fields and `auth_enabled` property |
| `apps/api/.env.example` | Replace the unused block with the three variables and how to derive them from the project ref |
| `apps/api/tests/test_config_auth.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `Settings · auth_enabled is false when nothing is configured` | Default instance |
| `Settings · auth_enabled is true when JWKS URL and issuer are set` | Both provided |
| `Settings · auth_enabled is false when only the issuer is set` | Negative: partial config |
| `Settings · audience defaults to authenticated` | Default value |
| `Settings · reads values from environment variables` | `monkeypatch.setenv` round trip |

## Green

1. Fields with defaults; tests 1 and 4.
2. `auth_enabled`; tests 2 and 3.
3. Env test; `.env.example` update.

## Refactor gate

`Settings` stays a flat field list; the property is one expression. Report the outcome.

✅ No refactor needed — three new fields plus a one-expression property; `Settings` stays a flat field list.

## Verification

```bash
cd apps/api && python -m pytest tests/test_config_auth.py
cd ../.. && ./ci.sh
```

## Out of scope

Reading the values (chapter 3), web variables (chapter 9), secrets management on Render.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-settings
```

```text
test(api): describe auth settings and the auth_enabled switch

feat(api): add Supabase JWT settings
```
