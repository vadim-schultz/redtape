---
id: C0
depends_on: []
touches:
  - ci.sh
  - apps/api/tests/test_suggestions_submit.py
execution: chapter-implementer
todos:
  - ch00-ci-baseline
---

# Chapter 0 — CI baseline

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)

**Batch:** B0 · **Execution:** chapter-implementer · **Status:** planned

## Goal

Make the API gate pass on a fresh database. The category round-trip test assumes a seeded taxonomy, and `ci.sh` runs pytest against the developer's `redtape` database. A fresh run therefore fails with 422. This chapter makes the test self-sufficient and isolates the pytest database.

## Boundaries

- `depends_on`: none.
- `touches`: `ci.sh`, `apps/api/tests/test_suggestions_submit.py`.
- Do not edit: the ledger, other chapter files, the release PR, or any other test file.
- Do not add a seed step to a shared fixture for other tests. Seed only where this test needs it.

## Red

- **Happy path:** on an empty database, `test_category_codes_round_trip_with_their_confidence_and_pvog_leaf_codes` returns 422 instead of 201. Run it against an empty `redtape_pytest` database and confirm the 422.
- **Negative path:** `test_an_unknown_category_code_is_a_422_that_names_the_code` keeps passing on an empty database. This test protects the failure path while the happy path is fixed.

Confirm both results before any production change. The happy-path failure must be the missing taxonomy, not a setup error.

## Green

- Seed the canonical taxonomy at the start of the round-trip test.
- In `ci.sh`, create and drop a dedicated `redtape_pytest` database for pytest, the same way the script already handles `redtape_migrations`.
- The developer's `redtape` database is no longer the pytest target. The `DATABASE_URL` for pytest is set to `redtape_pytest` (currently set to `redtape`, around line 60).

## Refactor

- Check that seeding is not duplicated across fixtures. If two tests seed the same data, move the call into one helper.
- Behaviour must not change. No new tests in this step.
- Refactor audit: the test module and the `ci.sh` pytest block.

## Gate

- Run the test file on a fresh `redtape_pytest` database: `uv run pytest tests/test_suggestions_submit.py` in `apps/api`.
- Run `./ci.sh` from the repository root. It must exit 0.
- Record the red and green results, the refactor outcome, and the integration commit in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- The developer's `redtape` database is already at head. This chapter must not change its state.
- Later chapters rely on `redtape_pytest` being recreated each run.
