# Discovery layer (chief of staff)

This suite is orchestrated as a **chief of staff** plan, not a `/loop` sentinel runbook.

Plan suite folder: `.plans/discovery-layer/` on `main` (architecture, rollout, chapters, ledger).

**Loop branch:** `feat/plans-discovery-layer`  
**Release branch:** `main`

## How to run

1. Merge the plan suite on `main` (if not already present).
2. Bootstrap the loop branch per the chief-of-staff `git-model.md` skill.
3. Launch **chief of staff** with plan folder `.plans/discovery-layer/`.
4. One **chapter-implementer** per chapter; each PR targets the loop branch only.
5. When the ledger is complete, open the release PR **loop branch → `main`**.

Day-to-day operator steps (migrations, ingest CLIs, admin smoke, machine emit) live in
[`discovery-layer.md`](../discovery-layer.md), not here.
