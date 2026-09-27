---
name: CI Foundation — Gaps and decisions
overview: "Settled decisions and open seams for running database tests on Postgres and verifying migrations in CI."
isProject: false
---

# CI Foundation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | CI uses a Postgres **service container** (`postgres:16-alpine`), not the SQLite file. SQLite is dropped as a test target for the API; the schema is Postgres-only by design ([document-matrix architecture](../document-matrix/00-architecture.md): "Postgres only"). |
| D2 | A missing database is an error when `REQUIRE_DB=1` and a skip otherwise. CI always sets it; local runs without Postgres keep working. Rejected: removing the skip entirely (breaks contributors without Docker) and detecting CI via `CI=true` (implicit, harder to reason about). |
| D3 | Test schema stays `Base.metadata.create_all`. Alembic correctness is verified by the separate round-trip job, not by driving every test through migrations (slower, and it would couple every test to migration history). The job also compares `alembic upgrade head` against `metadata` with `alembic check`, so model and migration cannot drift. |
| D4 | The round-trip job asserts a **single Alembic head**. Later suites (auth, suggestions, evidence, voting) each add migrations on parallel branches; two heads must fail the PR, not surface at deploy time. |
| D5 | `ci.sh` mirrors the workflow: same env variable names, same commands. The workflow file remains the source of truth (existing comment in `ci.sh` already says so). |

## Open seams

- **Test-suite duration.** Postgres-backed tests are slower than skipped ones. If `pytest` exceeds ~2 minutes
  in CI, evaluate `pytest-xdist` with per-worker schemas; not built now.
- **Local Docker requirement.** `ci.sh` starting compose assumes Docker is installed; the fallback message
  must explain the `REQUIRE_DB` opt-out instead of failing opaquely.
- **Web tests.** Unaffected; no browser or e2e layer is added here.
