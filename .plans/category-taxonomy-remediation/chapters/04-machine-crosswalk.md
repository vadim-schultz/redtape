---
id: C4
depends_on:
  - C1
touches:
  - apps/api/app/features/discovery/taxonomy_machine_controller.py
  - apps/api/app/schema/taxonomy/read.py
  - apps/api/app/features/taxonomy/service.py
  - apps/api/tests/test_discovery_taxonomy_route.py
  - apps/api/tests/test_machine_contract_fixture.py
  - apps/web/src/test/contract/openapi.schemas.json
  - apps/discovery-ingest/discovery_ingest/pvog/category_mapping.py
  - apps/discovery-ingest/discovery_ingest/client/candidates_api.py
  - apps/discovery-ingest/discovery_ingest/harvest/pvog.py
  - apps/discovery-ingest/tests/test_pvog_harvest.py
  - .plans/category-taxonomy-migration/category-contract-v1.json
execution: chapter-implementer
todos:
  - ch04-machine-crosswalk
---

# Chapter 4 — Machine crosswalk and ingest fetch (M2, ingest half)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** D-R2 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B2 · **Execution:** chapter-implementer · **Status:** planned

## Goal

Ingest must stop reading a file from the repository. The machine taxonomy endpoint serves the PVOG leaf crosswalk with its source version. Ingest fetches it once per harvest, validates it, and refuses to start when the fetch or the validation fails. The `.plans` copy is then deleted.

## Boundaries

- `depends_on`: C1.
- `touches`: the machine taxonomy controller, schema, and service; the route and contract tests; the OpenAPI snapshot; the ingest `category_mapping.py`, `candidates_api.py`, `harvest/pvog.py`, and its test; the `.plans` artifact copy (deleted here).
- Do not change the PVOG leaf states. That is C9.
- Do not change the review-state handling in `situation_mapping.py`. That is C7.

## Red

- **Happy path:** the machine vocabulary response carries the PVOG leaf crosswalk and its source version. A harvest with a fetched crosswalk maps a complete PVOG path to the expected categories.
- **Negative path (two cases):**
  - when the endpoint is unreachable, harvest refuses to start and writes no mentions;
  - when the response fails validation, harvest refuses to start and writes no mentions.
  - Also: no ingest module references the artifact path. This is checked by a search test.

## Green

- One fetch-and-validate client method, cached once per harvest run.
- Regenerate the OpenAPI snapshot in `apps/web/src/test/contract/openapi.schemas.json` and the machine contract fixture.
- Delete `.plans/category-taxonomy-migration/category-contract-v1.json`.
- The transitional hash test from C1 is removed with the `.plans` copy.

## Refactor

- One parsing path for the crosswalk. Both the harvest and any other ingest caller use the same parser.
- Refactor audit: `harvest/pvog.py` and `pvog/category_mapping.py`. Check that the file path constant is gone.

## Gate

- Backend: in `apps/api`, the taxonomy route and contract tests, plus `uv run mypy app scripts`.
- Ingest: in `apps/discovery-ingest`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy discovery_ingest`, and `uv run pytest tests/test_pvog_harvest.py`.
- Then `./ci.sh`.
- Record results in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md). Ingest runs fixture-only in CI, so the endpoint call is not made by tests.

## Notes

- C12 fixes the links that point to the deleted `.plans` file.
- C7 depends on this chapter. Legacy removal happens on top of the fetched crosswalk.
