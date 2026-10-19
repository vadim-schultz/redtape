---
name: "Chapter 4 — ci.sh local Postgres"
overview: "Pin DATABASE_URL for API pytest in ci.sh to match GHA; keep ingest tests on local mock list."
todos:
  - id: ci-sh
    content: "ci.sh pytest env DATABASE_URL + REQUIRE_DB"
    status: pending
  - id: docs
    content: "local-development.md note on .env vs ci.sh"
    status: pending
isProject: false
---

# Chapter 4 — ci.sh local Postgres

**Repo:** `redtape` (`ci.sh`, `apps/api`) · **Branch:** `feat/discovery-online-smoke-ci-postgres` · **Status:** planned

**Depends on:** none (parallel with 2–3) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Related:** [ci-foundation ch.1](../../ci-foundation/chapters/01-postgres-in-ci.md)

**Loop branch:** `feat/plans-discovery-online-smoke`

---

## Goal

`./ci.sh` API pytest never uses a **remote** `DATABASE_URL` from `apps/api/.env`. `test_api_key_service` and other DB tests run against **127.0.0.1:5432** like GHA.

**Not in scope:** `test_api_key_service` does not call external HTTP — only SQLAlchemy via [`db_session`](../../../apps/api/tests/conftest.py).

## Design decisions

Match [`.github/workflows/api-lint-test.yml`](../../../.github/workflows/api-lint-test.yml):

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape
REQUIRE_DB=1
```

Keep ruff/mypy `sqlite:///test.db` prefix unchanged. Discovery-ingest `pytest` file list in `ci.sh` unchanged (already local mocks).

Optional follow-up (not required): `conftest` guard rejecting non-localhost DSN when `REQUIRE_DB=1`.

## Files

| Path | Change |
| --- | --- |
| [`ci.sh`](../../../ci.sh) | Export `DATABASE_URL` + `REQUIRE_DB` on `uv run pytest` line |
| [`docs/operations/local-development.md`](../../../docs/operations/local-development.md) | One paragraph: CI overrides `.env` for tests |

## TDD loop

| Test | Asserts |
| --- | --- |
| `test_api_key_service · issue and verify` | Passes quickly on local Postgres |
| Existing `test_db_required.py` | Still green if present |

## Refactor gate

No production code — report no refactor needed.

## Verification

```bash
./ci.sh
cd apps/api && DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape \
  REQUIRE_DB=1 uv run pytest tests/test_api_key_service.py -q
```

## PR

Target loop branch.
