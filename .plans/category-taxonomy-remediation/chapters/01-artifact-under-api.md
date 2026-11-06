---
id: C1
depends_on:
  - C0
touches:
  - apps/api/app/shared/taxonomy/
  - apps/api/app/shared/category_codes.py
  - apps/api/scripts/seed_data/category_contract.py
  - apps/api/tests/test_seed_taxonomy.py
  - .plans/category-taxonomy-migration/category-contract-v1.json
execution: chapter-implementer
todos:
  - ch01-artifact-under-api
---

# Chapter 1 — Contract artifact under `apps/api`

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** D-R2, D-R5 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B1 · **Execution:** chapter-implementer · **Status:** planned

## Goal

Move the category contract out of `.plans/` and into `apps/api`, where the application reads it. Remove the dependency of `app` on `scripts`. Make the artifact load lazy and cached, instead of reading a file at import time.

## Boundaries

- `depends_on`: C0.
- `touches`: `apps/api/app/shared/taxonomy/` (new), `apps/api/app/shared/category_codes.py`, `apps/api/scripts/seed_data/category_contract.py`, `apps/api/tests/test_seed_taxonomy.py`, and the `.plans` artifact copy.
- The `.plans` copy is kept until C4 deletes it. C1 must not delete it.
- Do not change the content of the category inventory or the legacy crosswalk. The content is frozen (D-R5).
- Do not edit the PVOG leaf states here. That is C9.

## Red

- **Happy path:** importing `app.shared.category_codes` with `scripts` blocked (for example, a test import hook that raises on any `scripts` import) succeeds, and it yields the same 34 active codes as before.
- **Negative path:** a missing or malformed artifact raises a typed contract error on first use. It never yields an empty vocabulary.
- **Transitional guard (not a loop pair):** the `.plans` copy and the `apps/api` copy are byte-identical. C4 removes this test together with the `.plans` copy.

Confirm the happy and negative tests fail for the right reason (the import of `scripts` and the missing module), before green.

## Green

- Move the loader and the artifact to `apps/api/app/shared/taxonomy/category_contract_v1.json`.
- `app` stops importing `scripts`. `scripts` imports from `app`.
- Keep the `.plans` copy in place until C4.

## Refactor

- Replace the import-time file reads in `scripts/seed_data/category_contract.py` and `app/shared/category_codes.py` with one loader that is lazy and cached.
- Make the loader the only code that opens the artifact.
- Refactor audit: the loader module, `category_codes.py`, and `category_contract.py`, since all three touch the artifact.
- No new behaviour. Re-run the narrow suite after each extraction.

## Gate

- Backend: in `apps/api`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy app scripts`, and `uv run pytest tests/test_seed_taxonomy.py`.
- Then `./ci.sh` from the repository root.
- Record results in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- C9 also edits `test_seed_taxonomy.py`. C9 starts only after C1 is integrated.
- The frozen sections (inventory and legacy crosswalk) are hashed in C9 to prove the leaf-state edit does not change them.
