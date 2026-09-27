---
name: "Chapter 7 — API key model and hashing"
overview: "api_key table storing only SHA-256 hashes, an ApiKeyService that issues, verifies and revokes keys, and a script that prints a new key exactly once."
todos:
  - id: model
    content: "ApiKey model and migration"
    status: pending
  - id: service
    content: "ApiKeyService issue, verify, revoke"
    status: pending
  - id: script
    content: "scripts/issue_api_key.py"
    status: pending
isProject: false
---

# Chapter 7 — API key model and hashing

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/auth-api-keys` · **Status:** planned

**Depends on:** [2](02-user-model-migration.md) (migration chain) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Crawlers get a credential that is independent of any human account, can be revoked, and is never stored in
recoverable form (D7).

## Design decisions

**Key format**: `rt_` + 32 random bytes, URL-safe base64 without padding (`secrets.token_urlsafe(32)`). The
first 8 characters after the prefix are stored as `key_prefix` so operators can recognise a key in
listings without seeing it.

**Hash**: hex SHA-256 of the full string. Verification hashes the presented key and looks up
`key_hash`; comparison uses the database unique index plus `hmac.compare_digest` on the fetched hash to keep
timing uniform. Keys carry 256 bits of entropy, so salting or a slow KDF adds cost without benefit.

**Revoked or unknown keys are indistinguishable** to the caller (both fail verification with the same
`ApiKeyError`). `last_used_at` is updated on successful verification, at most once per minute to avoid a
write per crawler request.

**Layering.** `ApiKeyRepository` (queries) → `ApiKeyService` (generate, hash, verify, revoke). The issuing
script is a thin CLI, seed-script style, printing the plaintext once and never logging it.

**Migration** `<date>_api_key`, chained off the current head, reversible. Table shape in
[architecture §5](../00-architecture.md).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/api_key.py`, `apps/api/app/models/__init__.py` | Model and export |
| `apps/api/alembic/versions/<date>_api_key.py` | Table and unique index |
| `apps/api/app/features/auth/repository.py` | `ApiKeyRepository` |
| `apps/api/app/features/auth/service.py` | `ApiKeyService` |
| `apps/api/scripts/issue_api_key.py` | CLI: `--name crawler-prod`, `--revoke <prefix>` |
| `apps/api/tests/test_api_key_service.py`, `apps/api/tests/test_issue_api_key_script.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `ApiKeyService · issue returns a key starting with rt_` | Format |
| `ApiKeyService · issue stores only the hash, never the plaintext` | No column contains the key |
| `ApiKeyService · issued keys are unique` | Two issues differ |
| `ApiKeyService · verify accepts an issued key` | Returns the `ApiKey` row |
| `ApiKeyService · verify rejects an unknown key` | `ApiKeyError` |
| `ApiKeyService · verify rejects a revoked key` | Same error type as unknown |
| `ApiKeyService · verify updates last_used_at at most once per minute` | Two calls, one write |
| `ApiKey · duplicate hash is rejected` | `IntegrityError` |
| `issue_api_key script · prints the key once and exits 0` | Stdout contains `rt_`, DB contains hash only |
| `issue_api_key script · revoke marks the key revoked` | `revoked_at` set |

## Green

1. Model and migration; test 8.
2. Service `issue` and `verify`; tests 1–5.
3. Revocation and `last_used_at` throttle; tests 6–7.
4. Script; tests 9–10.

## Refactor gate

- `_hash(key)`, `_generate()` are separate one-liners; `verify` ≈ 5 LOC.
- The `last_used_at` throttle is its own method, not inline branching.
- Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_api_key_service.py tests/test_issue_api_key_script.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

The HTTP guard (chapter 8), scopes/permissions per key, expiry dates, key listing UI.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/auth-api-keys
```

```text
test(api): describe API key issue, verify and revoke

feat(api): add hashed API keys and the issue script
```
