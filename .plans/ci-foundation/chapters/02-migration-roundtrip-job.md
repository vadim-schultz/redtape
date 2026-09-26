---
name: "Chapter 2 — Migration round-trip job"
overview: "Every PR applies Alembic migrations to an empty Postgres, downgrades the newest one and upgrades again, checks for a single head and for model/migration drift."
todos:
  - id: script
    content: "scripts/check_migrations.sh with the four checks"
    status: pending
  - id: job
    content: "Workflow job calling it against a fresh Postgres service"
    status: pending
  - id: ci-sh
    content: "ci.sh runs the same script"
    status: pending
isProject: false
---

# Chapter 2 — Migration round-trip job

**Repo:** `redtape` (`apps/api`, `.github/workflows`, `ci.sh`) · **Branch:** `feat/ci-foundation-migrations` · **Status:** planned

**Depends on:** [1](01-postgres-in-ci.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A PR that adds a broken, irreversible or forked migration fails CI. Today only the nightly
[openplz-import.yml](../../../.github/workflows/openplz-import.yml) ever runs `alembic upgrade head`.

## Design decisions

**One script, two callers.** `apps/api/scripts/check_migrations.sh` runs, in order, against the configured
`DATABASE_URL`:

1. `alembic heads` prints exactly one head (D4).
2. `alembic upgrade head` on an empty database.
3. `alembic downgrade -1` then `alembic upgrade head` (round trip of the newest revision).
4. `alembic check` (no model/migration drift, D3).

The workflow job and `ci.sh` both call it, so local and CI behaviour cannot diverge (D5).

**Fresh database.** The job uses its own Postgres service and database, separate from the pytest job, so
`create_all` from the test run cannot mask a missing migration.

**Revision ids equal filenames** in this repo (`20260625_taxonomy`); the head check therefore also reads
well in logs. New revisions chain off `20260625_taxonomy` until later suites add theirs.

**Known risk.** `alembic check` may report drift that already exists in `main` (server defaults, enum
ordering). If so, the drift is fixed in this chapter by an additive migration, or the specific comparison
is narrowed with a documented `include_object` filter in `alembic/env.py`. Record which in the PR; do not
disable the check.

## Files

**Add** — `apps/api/scripts/check_migrations.sh`, `apps/api/tests/test_check_migrations_script.py`.

**Edit** — `.github/workflows/api-lint-test.yml` (new `migrations` job), `ci.sh` (call the script),
possibly `apps/api/alembic/env.py` (`include_object`, only if drift analysis requires it).

## Red tests

| Test | Asserts |
| --- | --- |
| `check_migrations · passes on the current migration chain` | Exit code 0 on a fresh database |
| `check_migrations · fails when two heads exist` | Temp revision branching off an old id → non-zero exit, message names both heads |
| `check_migrations · fails when a downgrade is not implemented` | Temp revision with `pass` in `downgrade` and a created table → the round trip leaves the table behind → non-zero |
| `check_migrations · fails when a model has no migration` | Temp model column not migrated → `alembic check` reports drift → non-zero |
| `check_migrations · does not touch the pytest database` | Script uses a separate database name, tests' data survives |

Tests copy the versions directory to a temp dir and point `ALEMBIC_CONFIG`/script location at it, so the
real chain is never modified.

## Green

1. Script with checks 1–2; first test and the two-heads test pass.
2. Add the round trip; the downgrade test passes.
3. Add `alembic check`; the drift test passes (and fix existing drift, see Design decisions).
4. Workflow job and `ci.sh` wiring.

## Refactor gate

- Script is four named functions of ≤ ~5 lines each, one concern per check, `set -euo pipefail`.
- Tests share one helper that builds the temp chain; no duplicated setup.
- Report the outcome explicitly.

## Verification

```bash
docker compose up -d --wait db
cd apps/api
bash scripts/check_migrations.sh
python -m pytest tests/test_check_migrations_script.py
cd ../.. && ./ci.sh
```

Manual: the PR shows a separate `migrations` job, green.

## Out of scope

Data migrations against production-like volumes, migration linting rules (lock timeouts, concurrent
indexes), running the seed scripts in CI.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/ci-foundation-migrations
```

```text
test(api): describe migration round trip, single head and drift checks

feat(api): add migration check script

ci: run the migration check as its own job
```
