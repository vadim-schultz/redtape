---
name: "Chapter 3 — JWT verifier"
overview: "A database-free JwtVerifier that validates a Supabase access token against the project's JWKS and returns typed claims, rejecting expired, mis-issued, wrong-audience, wrongly signed and unsigned tokens."
todos:
  - id: claims
    content: "TokenClaims and AuthError"
    status: pending
  - id: verifier
    content: "JwtVerifier with PyJWKClient"
    status: pending
  - id: dep
    content: "PyJWT[crypto] dependency"
    status: pending
isProject: false
---

# Chapter 3 — JWT verifier

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/auth-jwt-verifier` · **Status:** planned

**Depends on:** [1](01-settings-and-supabase-config.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3–4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`JwtVerifier.verify(token) -> TokenClaims(sub, email, display_name)` or raises `AuthError`. Pure logic:
no session, no request, no Litestar imports.

## Design decisions

**PyJWT with `PyJWKClient`** (D2). Added to `pyproject.toml` as `PyJWT[crypto]`. The key source is injected
as a small `KeyResolver` callable (`token -> key`) so tests supply an in-memory key and never hit the
network; production wiring passes `PyJWKClient(settings.supabase_jwks_url, cache_keys=True).get_signing_key_from_jwt`.
Rejected: mocking `requests`/`urllib` (mocks what we do not own) and a hand-written JWKS fetcher.

**Algorithms are an allow-list**: `["RS256", "ES256"]`. `alg: none` and `HS256` tokens are rejected before
verification.

**Required claims**: `exp`, `iat`, `sub`, `iss`, `aud`. `iss` must equal `supabase_jwt_issuer`, `aud` must
equal `supabase_jwt_audience`. A small clock leeway (10 s) is a named constant, not a setting.

**One error type.** Every failure raises `AuthError(reason)` with a short machine-readable `reason`
(`expired`, `bad_signature`, `bad_audience`, `bad_issuer`, `malformed`, `unsupported_alg`,
`missing_claim`). Controllers later map it to 401 without leaking detail beyond the reason code.

**Email and name come from the token** (`email`, `user_metadata.full_name`) and are optional in
`TokenClaims`; `sub` and `email` are required for our purposes (a token without an email is rejected).

## Files

| Path | Change |
| --- | --- |
| `apps/api/pyproject.toml` | `PyJWT[crypto]` |
| `apps/api/app/features/auth/__init__.py` | New package |
| `apps/api/app/features/auth/jwt.py` | `TokenClaims`, `AuthError`, `JwtVerifier` |
| `apps/api/tests/test_jwt_verifier.py` | Tests below; helper generating an RSA key and signing tokens |

## Red tests

| Test | Asserts |
| --- | --- |
| `JwtVerifier · accepts a valid token and returns sub and email` | Happy path |
| `JwtVerifier · rejects an expired token` | `reason == "expired"` |
| `JwtVerifier · rejects a token signed by another key` | `bad_signature` |
| `JwtVerifier · rejects a wrong audience` | `bad_audience` |
| `JwtVerifier · rejects a wrong issuer` | `bad_issuer` |
| `JwtVerifier · rejects alg none` | `unsupported_alg` |
| `JwtVerifier · rejects an HS256 token signed with the public key text` | Algorithm-confusion attack fails |
| `JwtVerifier · rejects a token without sub` | `missing_claim` |
| `JwtVerifier · rejects a token without email` | `missing_claim` |
| `JwtVerifier · rejects a non-JWT string` | `malformed` |
| `JwtVerifier · accepts a token within clock leeway of expiry` | Boundary |

## Green

1. Claims and error types, happy path.
2. One rejection at a time in the table order; each is one small branch mapped through a single
   `_translate(exc)` function.
3. Production key resolver factory `jwks_key_resolver(url)`, tested only for wiring (returns a callable),
   not for network.

## Refactor gate

- Rejections funnel through `_translate`, a dict from PyJWT exception type to reason: no if-chain
  (rule of three).
- `verify` ≈ 5 LOC: decode, build claims. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_jwt_verifier.py
cd ../.. && ./ci.sh
```

## Out of scope

HTTP integration (chapter 4), user upsert, refresh tokens.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-jwt-verifier
```

```text
test(api): describe JWT verification and rejection reasons

feat(api): add JwtVerifier for Supabase access tokens
```
