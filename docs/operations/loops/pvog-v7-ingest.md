# PVOG v7 ingest (chief of staff)

Restore **Platform maintenance** discovery job **PVOG Suchdienst catalogue run** after PVOG Suchdienst v7 API contract changes (required Lebenslagen search, `serviceDescriptions` wrapper).

Plan suite: [`.plans/pvog-v7-ingest/`](../../../.plans/pvog-v7-ingest/) on `main`.

**Loop branch:** `feat/plans-pvog-v7-ingest`  
**Release branch:** `main`

**Prerequisite:** [discovery-online-smoke](discovery-online-smoke.md) complete (GovData batch + jurisdiction secret).

## How to run

1. Merge the plan suite on `main` (if not already present).
2. Bootstrap loop branch per chief-of-staff `git-model.md`.
3. Launch **chief of staff** with plan folder `.plans/pvog-v7-ingest/`.
4. One **chapter-implementer** per chapter; each PR targets the loop branch only.
5. When the ledger is complete, open release PR **loop branch → `main`**.

## Status

Planned — three chapters (client tree walk, row mapping, docs).

## Exit criteria

- `python -m discovery_ingest pvog run` succeeds against live Suchdienst (operator or GHA).
- **Platform maintenance** `job=discovery` passes **PVOG Suchdienst catalogue run** and **Discovery worker drain**.
- Canon documents federal ingest as **facades bootstrap → leaf personalMatter codes → paginated v7 search**.
