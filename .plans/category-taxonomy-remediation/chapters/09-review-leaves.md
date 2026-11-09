---
id: C9
depends_on:
  - C1
touches:
  - apps/api/app/shared/taxonomy/category_contract_v1.json
  - apps/api/tests/test_seed_taxonomy.py
  - apps/discovery-ingest/tests/test_pvog_situation_mapping.py
execution: chapter-implementer
todos:
  - ch09-review-leaves
---

# Chapter 9 — Review-state PVOG leaves accepted (M8)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** D-R5, D-R9 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B2 (starts after C1 is integrated) · **Execution:** chapter-implementer · **Status:** planned

## Goal

Fourteen PVOG leaves are in `review` state in the contract artifact. Keep them published (D-R9), but record a reason and an acceptance date for each one, and make artifact validation reject any leaf that is in `review` without a reason.

## Boundaries

- `depends_on`: C1.
- `touches`: the artifact under `apps/api/app/shared/taxonomy/`, `test_seed_taxonomy.py`, and `test_pvog_situation_mapping.py`.
- Do not change the category inventory or the legacy crosswalk. They are frozen (D-R5).
- Do not change harvest behaviour. Harvest still emits the evidence for each leaf.

## Red

- **Happy path:** every PVOG leaf mapping is `mapped`, with a non-empty reason and an `accepted_on` date.
- **Negative path:** a leaf left in `review` without a reason fails artifact validation with an error that names the leaf.
- **Also (harvest evidence):** every leaf has a disposition, and harvest still emits its evidence for each leaf. This is part of the happy-path test.

## Green

- Update the 14 leaves per D-R5 and D-R9. Add the acceptance fields: `reason` and `accepted_on`.
- Keep the leaf states in the artifact. Do not move them out of the file.

## Frozen-section check (before and after)

- Hash the frozen sections (category inventory and legacy crosswalk) before the edit, and again after it. The two hashes must match.
- Record both hashes in the ledger row for C9. A mismatch blocks integration.

## Refactor

- None expected. State that in the ledger row.
- If the validation grows a branch per leaf state, extract a named predicate instead of adding an arm.

## Gate

- Backend: in `apps/api`, `uv run pytest tests/test_seed_taxonomy.py`, plus ruff and mypy.
- Ingest: in `apps/discovery-ingest`, `uv run pytest tests/test_pvog_situation_mapping.py`, plus ruff and mypy.
- Then `./ci.sh`.
- Record results and the frozen-section hashes in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- C9 edits `test_seed_taxonomy.py`, which C1 also edits. C9 starts only after C1 is integrated.
- C9 and C7 both touch `test_pvog_situation_mapping.py`. C9 integrates before C7 (see the shared-file serials in [../01-rollout.md](../01-rollout.md)).
