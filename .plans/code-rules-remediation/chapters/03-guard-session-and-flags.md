---
name: "Chapter 3 — Guard session and flags"
overview: "One shared guard-session helper; split feature-flag checks from the allowlist check; replace principal: object."
todos:
  - id: characterize
    content: "Pin guard outcomes: 200 admin, 403 non-admin, 503 disabled, 401 unauthenticated"
    status: pending
  - id: shared-session
    content: "Shared helper for guards that need a DB session"
    status: pending
  - id: split-flags
    content: "Flag checks and allowlist check are separate small guards"
    status: pending
isProject: false
---

# Chapter 3 — Guard session and flags

**Repo:** `redtape` · **Branch:** `refactor/guard-session-and-flags` · **Status:** planned

**Depends on:** chapter 1 · **Architecture:** [../00-architecture.md](../00-architecture.md) B3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

Guards stop wiring sessions and services by hand. The three copies of "open `SessionLocal`, build repository and service, commit" collapse into one helper, and each guard does one thing. Recent history matters: `0ba9c09` fixed the admin guard reading a detached user after its session closed; keep that behaviour (read what you need before the session closes) and its regression test (`73c8bb3`).

## Files

- `apps/api/app/auth/guards.py` — `require_role` opens its own `SessionLocal` (about lines 27-30, 42-44).
- `apps/api/app/features/discovery/guards.py` — `require_discovery_admin` (about lines 99-111) opens `SessionLocal`, builds `UserService(UserRepository(session))`, reads `settings`, and mixes `discovery_enabled` and `auth_enabled` checks with the allowlist decision.
- `apps/api/app/features/suggestions/controller.py:68` — `principal` typed as `object` and cast.
- Tests: `apps/api/tests/test_discovery_admin_api.py` and the guard tests (see `73c8bb3`).
- New: `apps/api/app/auth/guard_session.py` (a context manager or dependency yielding the user service), small, with docstring.

## TDD loop

### Red

1. Happy path: allowlisted admin gets 200 on an admin route, with a closing session (the `73c8bb3` scenario).
2. Negative paths: non-admin 403; `discovery_enabled=false` 503; auth disabled / no token 401; no session left open in any case.
3. Type check: `principal` has a precise type (the authenticated principal class or a `Protocol`), no `cast`.

Pin the current outcomes first (they pass), then refactor.

### Green

1. Add the shared session helper; make `auth/guards.py` and `discovery/guards.py` use it.
2. Split `require_discovery_admin` into a flag guard (503/401) and an allowlist guard (403), composed in the route's guard list.
3. Replace `principal: object` with the real type.

### Refactor

Audit both guard modules: about 5 lines per function, no boolean flags, one nesting level, docstrings on public symbols. Report guard function line counts before and after and the number of `SessionLocal` call sites (expected: one).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_discovery_admin_api.py
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/guard-session-and-flags
```

```text
test(api): pin discovery admin guard outcomes
refactor(api): share one guard session helper and split flag checks from the allowlist
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`.
