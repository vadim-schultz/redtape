---
name: "Chapter 1 — Postgres in CI"
overview: "API tests run against a Postgres service in GitHub Actions and in local ./ci.sh; an unreachable database fails the run when REQUIRE_DB=1 instead of skipping every DB test."
todos:
  - id: require-db
    content: "conftest: REQUIRE_DB turns the skip into a failure"
    status: completed
  - id: workflow
    content: "api-lint-test.yml: postgres service, DATABASE_URL, REQUIRE_DB"
    status: completed
  - id: ci-sh
    content: "ci.sh: stop forcing SQLite for pytest; start compose db when needed"
    status: completed
  - id: fallout
    content: "Fix any test that was silently skipped and now fails"
    status: completed
isProject: false
---

# Chapter 1 — Postgres in CI

**Repo:** `redtape` (`apps/api` tests, `.github/workflows`, `ci.sh`) · **Branch:** `feat/ci-foundation-postgres` · **Status:** done

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §1–3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Every DB-backed test in `apps/api/tests/` executes in CI and in local `./ci.sh`. A run that cannot reach the
database fails when `REQUIRE_DB=1` (always set in CI) and skips with a reason otherwise.

## Design decisions

**Fail-loud switch lives in the fixture.** `db_session` in
[conftest.py](../../../apps/api/tests/conftest.py) currently wraps `create_all` in `try/except` and calls
`pytest.skip`. A helper `_require_db()` returns `os.environ.get("REQUIRE_DB") == "1"`; the `except` branch
re-raises when it is true. Rejected: `CI=true` detection (implicit, also true on contributor forks that
lack Postgres).

**One workflow, service container.** `postgres:16-alpine` with `pg_isready` health options, port 5432,
credentials matching [docker-compose.yml](../../../docker-compose.yml). `DATABASE_URL` becomes
`postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape`. The SQLite pysqlite event hooks at the top
of `conftest.py` become dead for CI; they are **kept** here (removing them is D1 fallout for a later
cleanup, see [gaps](../gaps-and-decisions.md)) unless they block. Note this in the PR.

**Local `ci.sh`.** Drop the `DATABASE_URL="sqlite:///test.db"` prefix for the `pytest` invocation only (ruff
and mypy do not touch the database and may keep any value). Before pytest: if nothing listens on 5432, run
`docker compose up -d --wait db`; if Docker is missing, print how to opt out (`REQUIRE_DB=0`) and continue,
so contributors without Docker are not blocked.

**Fallout is in scope.** Tests hidden by the old skip may fail on first run (JSONB defaults, enum values,
unique constraints). Fix each in its own small commit with the failing assertion as the red step.

## Files

**Edit**

| Path | Change |
| --- | --- |
| `apps/api/tests/conftest.py` | `_require_db()`; re-raise when set |
| `.github/workflows/api-lint-test.yml` | `services.postgres`, env `DATABASE_URL`, `REQUIRE_DB: "1"` |
| `ci.sh` | pytest without SQLite override; ensure compose `db` |
| `apps/api/.env.example` | Note that tests need Postgres; document `REQUIRE_DB` |
| `docs/operations/local-development.md` | One paragraph: running tests locally |

**Add**

| Path | Change |
| --- | --- |
| `apps/api/tests/test_db_required.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `conftest · REQUIRE_DB=1 with an unreachable database raises instead of skipping` | Run the fixture body against a bad URL via a subprocess `pytest` invocation; exit code is non-zero and output has no "skipped" for the DB test |
| `conftest · REQUIRE_DB unset with an unreachable database skips with a reason` | Same setup; exit code 0, skip reason mentions "Database unavailable" |
| `conftest · db_session yields a working session against Postgres` | `SELECT 1` and `session.bind.dialect.name == "postgresql"` |
| `conftest · JSONB column round-trips through db_session` | Insert and read a `Document.title_i18n`; proves the schema is not SQLite-degraded |
| `conftest · test data does not leak between tests` | Two tests insert the same unique key; both pass (rollback works on Postgres) |

## Green

1. `_require_db()` and the re-raise; the first two tests pass.
2. Point the local run at Postgres; the last three tests pass.
3. Workflow service container, then `ci.sh`.
4. Run the full suite with `-rs`; fix each newly failing test (one commit each).

## Refactor gate

- `db_session` stays ≤ ~12 lines; the environment check is a named helper, not an inline condition.
- No dead SQLite branches left unexplained: either removed with a test proving nothing needs them, or
  called out in the PR as deliberately kept.
- Report the outcome, e.g. "✅ no refactor needed — one helper, one branch".

## Verification

```bash
docker compose up -d --wait db
cd apps/api
REQUIRE_DB=1 python -m pytest -rs        # zero DB skips
REQUIRE_DB=1 DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:1/redtape python -m pytest tests/test_db_required.py
cd ../.. && ./ci.sh
```

Manual: open the PR and confirm the workflow log shows the Postgres service starting and the pytest summary
lists no skipped DB tests.

## Out of scope

Migrations in CI (chapter 2), xdist, coverage thresholds, removing SQLite hooks unless they block.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/ci-foundation-postgres
```

```text
test(api): describe DB tests failing loudly when Postgres is required

feat(api): fail instead of skipping DB tests when REQUIRE_DB is set

ci: run API tests against a Postgres service and start compose db in ci.sh
```

## Outcome

- ✅ no refactor needed — `_require_db()` is one named helper, `db_session` keeps its one `except` branch
  (~14 lines including its docstring), no new nesting.
- SQLite pysqlite event hooks in `conftest.py` are kept as designed (dead under this workflow now, not
  removed here).
- Fallout, once run against a clean Postgres instead of the polluted local dev volume: four fixtures
  (`test_taxonomy_service.py`, `test_documents_filter.py`, `test_matrix_endpoint.py`, `test_taxonomy_api.py`)
  called `seed_taxonomy(db_session)` with its default document-tag map, which references
  `scripts/seed_documents.py`'s fixed document ids — a foreign key violation none of these fixtures ever
  seed. Always broken; always skipped before. Fixed with `tags={}` (one line, one commit each).
- A second, unrelated fallout: `test_taxonomy_api.py`'s HTTP fixture overrode the session dependency via
  `app.dependencies["session"] = Provide(...)` **after** calling `create_app()`. Litestar resolves and
  caches each route handler's dependency providers once, during `Litestar()` construction itself — a
  post-construction mutation of `app.dependencies` has no effect on handlers already built, so every
  request silently used a fresh, disconnected session that saw none of the test's (uncommitted) data.
  `test_documents_filter.py` and `test_matrix_endpoint.py` already used the pattern that actually works —
  `monkeypatch.setattr("app.main.provide_session", lambda: db_session)` **before** `create_app()` — so
  `test_taxonomy_api.py` was brought in line with them instead of inventing a third mechanism.
- Full suite: 100 passed, zero DB skips, both via `apps/api` `pytest -rs` and `./ci.sh`.
