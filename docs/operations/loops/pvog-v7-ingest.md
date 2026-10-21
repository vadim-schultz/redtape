# PVOG v7 ingest (chief of staff)

Align **discovery-ingest** PVOG Suchdienst catalogue fetch with v7 search and `serviceDescriptions` pagination so
**Platform maintenance** discovery runs succeed after GovData batch and jurisdiction smoke fixes.

Plan suite: [`.plans/pvog-v7-ingest/`](../../../.plans/pvog-v7-ingest/) on `main`.

**Loop branch:** `feat/plans-pvog-v7-ingest`  
**Release branch:** `main`

**Prerequisite:** [discovery-online-smoke](discovery-online-smoke.md) on `main` (GovData catalogue batch + `FEDERAL_JURISDICTION_ID`); production GHA fails on the PVOG step only.

## How to run

1. Merge the plan suite on `main` (if not already present).
2. Bootstrap the loop branch per the chief-of-staff `git-model.md` skill.
3. Launch **chief of staff** with plan folder `.plans/pvog-v7-ingest/`.
4. One **chapter-implementer** per chapter; each PR targets the loop branch only.
5. When the ledger is complete, open release PR **loop branch → `main`**.

## Status

In progress — three chapters (v7 client tree walk, row mapping, docs canon). Operator runbook:
[`discovery-online.md`](../discovery-online.md) (PVOG v7 search triage); canon:
[`government-data-sources.md`](../../discovery/government-data-sources.md) § Federal ingest.

## Exit criteria

- `gh workflow run platform-maintenance.yml -f job=discovery` succeeds through **PVOG Suchdienst catalogue run** and **Discovery worker drain**.
- GHA logs show v7 URLs with `personalMatters` / `facades` query parameters (no bare parameterless list).
- Optional: `source=pvog` rows visible in production `/admin/discovery/catalogue`.
