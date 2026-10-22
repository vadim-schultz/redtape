# Discovery admin remediation — Run ledger

**Loop branch:** `feat/plans-discovery-admin-remediation`
**Release branch:** `main`
**Release PR:** _(filled when opened)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file.

Use this ledger to record chapter implementation, verification, refactor outcome, and release status.

| Chapter | Branch / PR | Red → green evidence | Refactor outcome | CI / smoke | Status |
| --- | --- | --- | --- | --- | --- |
| 1. Live triage — probe and routes | `docs/discovery-admin-remediation-triage` / [#157](https://github.com/vadim-schultz/redtape/pull/157) | Probe 401 "Not authenticated" (operator-reported; origin unconfirmed); allowlist OK, MACHINE_OPT_IN=false. Likely cause: Supabase JWKS/issuer unset on Render (auth_enabled false) or Authorization dropped by proxy. Blank page reported (F1). Chapter 3 cause-specific part: no-go until operator checks Render Supabase vars | n/a (ops) | local ci pass; remote pass; merged | merged |
| 2. Route nesting fix | `fix/discovery-admin-route-nesting` / [#158](https://github.com/vadim-schultz/redtape/pull/158) | 2 real-App tests red (empty body) → green via relative routes under pathless guarded layout | Audited; no refactor needed | remote pass; local ./ci.sh red only from pre-existing flaky suggestions tests (timeouts under load, pass in isolation) | merged |
| 3. Admin probe resilience and menu feedback | `fix/discovery-admin-probe-resilience` | | | | planned |
| 4. Real-tree smoke and docs | `docs/discovery-admin-remediation-smoke` | | | | planned |

## Release gate

- [ ] All chapter tests and refactor outcomes recorded.
- [ ] `./ci.sh` passes on `feat/plans-discovery-admin-remediation`.
- [ ] Probe status for the operator email recorded and any Render config fix applied.
- [ ] Worker-origin admin API smoke passes with the expected `401`/`403`/`200` outcomes.
- [ ] Allowlisted user sees Catalogue, Coverage, and Tasks in the menu and all three pages render.
- [ ] Release PR opened from `feat/plans-discovery-admin-remediation` to `main`.
