---
name: "Chapter 8 — Machine principal guard"
overview: "An X-API-Key dependency and require_machine guard producing a MachinePrincipal, plus a provide_principal that accepts either a bearer user or an API key, so submission routes can serve both people and crawlers."
todos:
  - id: machine
    content: "provide_machine_principal from X-API-Key"
    status: pending
  - id: either
    content: "provide_principal: user or machine"
    status: pending
isProject: false
---

# Chapter 8 — Machine principal guard

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/auth-machine-guard` · **Status:** planned

**Depends on:** [4](04-current-user-dependency.md), [7](07-api-key-model-and-hashing.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §2–4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A route can accept `principal: Principal` and receive a `UserPrincipal` (Bearer) or `MachinePrincipal`
(`X-API-Key`), while human-only routes keep using `current_user` and reject keys (D8). This is the seam the
suggestion suite uses so one interface serves people and crawlers.

## Design decisions

**Small explicit types.** `Principal = UserPrincipal | MachinePrincipal`, frozen dataclasses in
`features/auth/principal.py`. `UserPrincipal(user: AppUser)`, `MachinePrincipal(api_key: ApiKey)`; both
expose `kind` (`"user"` or `"crawler"`) and `id`. Handlers branch on `kind`, never on `isinstance` chains
(one dispatch table in the suggestion suite).

**Order of evaluation for `provide_principal`**: if `Authorization` is present use the bearer path; else if
`X-API-Key` is present use the key path; else 401. **Both present → 400**, rather than guessing which one
the client meant.

**Failure shape** identical to chapter 4: 401 `{"detail": "Not authenticated"}` for unknown or revoked keys
and malformed headers; the reason goes to the log.

**Auth disabled** does not disable API keys: keys do not depend on Supabase. Human paths still 401.

**Machine-only routes** use `guards=[require_machine]` (for example a future crawler heartbeat); it returns
403 to a logged-in human, because credentials exist but are the wrong kind.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/auth/principal.py` | Types |
| `apps/api/app/features/auth/dependencies.py` | `provide_machine_principal`, `provide_principal` |
| `apps/api/app/features/auth/guards.py` | `require_machine` |
| `apps/api/tests/test_principal.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `principal · valid API key yields a machine principal` | `kind == "crawler"`, id is the key id |
| `principal · valid bearer token yields a user principal` | `kind == "user"` |
| `principal · no credentials returns 401` | Negative |
| `principal · both headers return 400` | Ambiguity refused |
| `principal · revoked key returns 401` | Same body as unknown |
| `principal · unknown key returns 401` | Same body as revoked |
| `principal · API key works when Supabase auth is disabled` | Independence |
| `current_user · rejects an API key with 401` | Human-only routes stay human-only |
| `require_machine · human token gets 403` | Wrong kind |
| `require_machine · API key passes` | 200 |

## Green

1. Types and `provide_machine_principal`; tests 1, 5, 6.
2. `provide_principal`; tests 2, 3, 4, 7.
3. Guard and the human-only assertion; tests 8–10.

## Refactor gate

- `provide_principal` is a two-branch dispatch of ≈5 LOC calling the two named providers; a third
  credential type would trigger extracting a registry (rule of three).
- Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_principal.py
cd ../.. && ./ci.sh
```

## Out of scope

Per-key scopes, rate limits per key, mTLS.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-machine-guard
```

```text
test(api): describe principal resolution for users and API keys

feat(api): add machine principal and require_machine guard
```
