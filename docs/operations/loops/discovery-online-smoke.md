# Discovery online smoke (chief of staff)

Fix production **GovData catalogue batch 500** during platform maintenance discovery runs, and align **local `./ci.sh`** with local-only Postgres for API tests.

Plan suite: [`.plans/discovery-online-smoke/`](../../../.plans/discovery-online-smoke/) on `main`.

**Loop branch:** `feat/plans-discovery-online-smoke`  
**Release branch:** `main`

**Prerequisite:** [discovery-online](discovery-online.md) loop complete (scheduled ingest on `main`).

## How to run

1. Merge the plan suite on `main` (if not already present).
2. Bootstrap the loop branch per the chief-of-staff `git-model.md` skill.
3. Launch **chief of staff** with plan folder `.plans/discovery-online-smoke/`.
4. One **chapter-implementer** per chapter; each PR targets the loop branch only.
5. Chapter **1** may be operator-only (secret + triage) before code chapters merge.
6. When the ledger is complete, open release PR **loop branch → `main`**.

## Status

Planned — four chapters. Operator runbook remains [`discovery-online.md`](../discovery-online.md); this suite patches production smoke and CI hygiene.

## Exit criteria

- `gh workflow run platform-maintenance.yml -f job=discovery` succeeds.
- Render logs show **201** for `POST /api/v1/discovery/machine/catalogue/batch`.
- `./ci.sh` does not require remote Postgres for API pytest.
