# Discovery online (chief of staff)

This suite is orchestrated as a **chief of staff** plan, not a `/loop` sentinel runbook.

Plan suite folder: `.plans/discovery-online/` on `main` (architecture, rollout, chapters, ledger).

**Loop branch:** `feat/plans-discovery-online`  
**Release branch:** `main`

## How to run

1. Merge the plan suite on `main` (if not already present).
2. Bootstrap the loop branch per the chief-of-staff `git-model.md` skill.
3. Launch **chief of staff** with plan folder `.plans/discovery-online/`.
4. One **chapter-implementer** per chapter; each PR targets the loop branch only.
5. When the ledger is complete, open the release PR **loop branch → `main`**.

## Status

All ten in-loop chapters are implemented on `feat/plans-discovery-online`. **Definition of done for
CoS:** merge the release PR to `main`, then sync or retire the loop branch per `git-model.md`.

Day-to-day operator steps (scheduled ingest, workflow dispatch, idempotency, admin smoke):
[`discovery-online.md`](../discovery-online.md).

**Prerequisite:** [discovery-layer](discovery-layer.md) loop complete (machine API and
`apps/discovery-ingest` on `main`).
