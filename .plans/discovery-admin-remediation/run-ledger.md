# Discovery admin remediation — Run ledger

**Loop branch:** `feat/plans-discovery-admin-remediation`
**Release branch:** `main`
**Release PR:** _(filled when opened)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file.

Use this ledger to record chapter implementation, verification, refactor outcome, and release status.

| Chapter | Branch / PR | Red → green evidence | Refactor outcome | CI / smoke | Status |
| --- | --- | --- | --- | --- | --- |
| 1. Live triage — probe and routes | `docs/discovery-admin-remediation-triage` | _(probe status and cause)_ | n/a (ops) | n/a | planned |
| 2. Route nesting fix | `fix/discovery-admin-route-nesting` | | | | planned |
| 3. Admin probe resilience and menu feedback | `fix/discovery-admin-probe-resilience` | | | | planned |
| 4. Real-tree smoke and docs | `docs/discovery-admin-remediation-smoke` | | | | planned |

## Release gate

- [ ] All chapter tests and refactor outcomes recorded.
- [ ] `./ci.sh` passes on `feat/plans-discovery-admin-remediation`.
- [ ] Probe status for the operator email recorded and any Render config fix applied.
- [ ] Worker-origin admin API smoke passes with the expected `401`/`403`/`200` outcomes.
- [ ] Allowlisted user sees Catalogue, Coverage, and Tasks in the menu and all three pages render.
- [ ] Release PR opened from `feat/plans-discovery-admin-remediation` to `main`.
