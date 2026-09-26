---
name: CI Foundation — Architecture
overview: "Make API database tests run against Postgres in CI and locally, fail loudly instead of skipping, and prove migrations round-trip. Prerequisite for the auth, suggestion, evidence, voting and crawler suites, whose models need JSONB and native enums."
isProject: false
---

# CI Foundation — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Problem

The API schema uses Postgres-only types (`JSONB`, native enums, partial-index style constraints; see
[20260625_taxonomy.py](../../apps/api/alembic/versions/20260625_taxonomy.py)). Yet both the GitHub workflow
([api-lint-test.yml](../../.github/workflows/api-lint-test.yml)) and [ci.sh](../../ci.sh) set
`DATABASE_URL=sqlite:///test.db`.

The `db_session` fixture in [conftest.py](../../apps/api/tests/conftest.py) calls `Base.metadata.create_all`
inside a `try`; on SQLite that raises (JSONB has no SQLite DDL), and the fixture calls `pytest.skip(...)`.
Result: **every DB-backed test is skipped in CI and in local `./ci.sh`, and the run is still green.**

The next five suites add write paths, unique constraints, vote tallies and idempotency keys. Those are
exactly the behaviours that only a real database verifies. Building them on skipped tests would ship
untested code behind a green check.

## 2. Target state

| Concern | Today | After this suite |
| --- | --- | --- |
| CI database | SQLite file | Postgres 16 service container, same major version as [docker-compose.yml](../../docker-compose.yml) |
| DB tests in CI | Silently skipped | Run; an unreachable DB **fails** the job (`REQUIRE_DB=1`) |
| Local `./ci.sh` | SQLite, DB tests skipped | Uses `DATABASE_URL` from the environment; starts the compose `db` service when none is set |
| Local dev without Postgres | Skip | Still skips, with a visible skip reason (unchanged; opt-out stays possible) |
| Migrations | Never executed in PR CI (only nightly OpenPLZ import runs `upgrade head`) | Every PR runs `upgrade head`, `downgrade -1`, `upgrade head` |
| Schema source in tests | `Base.metadata.create_all` | Unchanged (see D3); the round-trip job covers Alembic separately |

## 3. Design

- **Workflow.** `api-lint-test.yml` gains a `services: postgres` block with a health check, and
  `DATABASE_URL=postgresql+psycopg://…` plus `REQUIRE_DB=1`. The lint steps stay first so style failures
  surface before the database spins up.
- **Fail-loud switch.** `conftest.py` reads `REQUIRE_DB`. When set, a failing `create_all` re-raises instead
  of skipping. One small helper, `_require_db()`, keeps `db_session` under ~5 LOC of new logic.
- **Local gate.** `ci.sh` stops hard-coding SQLite for pytest. The `Settings` default in
  [config.py](../../apps/api/app/config.py) already points at the compose Postgres
  (`postgres:postgres@127.0.0.1:5432/redtape`), so `ci.sh` simply stops overriding `DATABASE_URL` for
  pytest; if the port is closed it runs `docker compose up -d --wait db`.
- **Migration job.** A second job (or step) in the same workflow points Alembic at a fresh database and
  round-trips the newest revision. It also asserts `alembic heads` returns exactly one head, so parallel
  suites cannot merge two heads unnoticed.

## 4. Out of scope

Async tests, test parallelism (xdist), coverage thresholds, secret scanning, deploy workflows, a
production-like data seed in CI, replacing `create_all` with Alembic in fixtures (see D3).
