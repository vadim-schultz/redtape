---
id: C2
depends_on:
  - C1
touches:
  - apps/api/scripts/category_backfill.py
  - apps/api/tests/test_category_backfill.py
execution: chapter-implementer
todos:
  - ch02-replay-merge
---

# Chapter 2 — Replay merge rule (M1)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** O2 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B2 · **Execution:** chapter-implementer · **Status:** planned

## Goal

A backfill replay must not overwrite a row that the promotion path wrote. Pre-C9 `DocumentRepository.add` wrote `document_category` rows with `source='promotion'` and provenance `{"source": "category_code_promotion"}`. The current replay can overwrite them. The rule is: keep the source and provenance, and keep the highest confidence.

## Boundaries

- `depends_on`: C1.
- `touches`: `apps/api/scripts/category_backfill.py`, `apps/api/tests/test_category_backfill.py`.
- Do not change the crosswalk, the score combination of `max` (O2), or the migration files. C3 owns the migration.

## Red

- **Happy path:** a replay over a `source='promotion'` row with confidence 0.9 and promotion provenance keeps `source`, provenance, and confidence 0.9 when the legacy projection is 0.6. A legacy-only pair still inserts with `source='legacy_crosswalk'`.
- **Negative path:** a replay with a crosswalk conflict writes no row for that pair and counts the conflict in the report. A second run (rerun) writes nothing new.

Confirm both fail for the right reason before implementing: the first on overwrite, the second on the missing conflict count.

## Green

- An existing non-legacy row keeps its `source` and provenance.
- Its confidence becomes the maximum of the stored value and the projection.
- The `max` rule stays the single score combination (O2).

## Refactor

- Extract `_merge_existing_link` from `_persist_links`. The merge rule lives in one named unit.
- Keep `_persist_links` within the branch budget: one decision per branch, no more than two arms for the same decision in the containing entity.
- Refactor audit: the whole of `category_backfill.py` for the upsert and projection paths, not only the changed lines. The existing `_add_projection` uses `max`; check that it and the new merge share one definition.
- No new tests in this step.

## Gate

- Backend: `uv run pytest tests/test_category_backfill.py` in `apps/api`, plus ruff and mypy on `scripts`.
- Then `./ci.sh`.
- Run the tests on a disposable database. Do not run them against the developer's `redtape` database.
- Record red and green results, the refactor outcome, and the integration commit in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- C3 depends on this rule. C3's migration replays the backfill, so an overwrite here would reach the migration.
- C13 checks whether promotions ran after this chapter. See [../run-ledger.md](../run-ledger.md).
