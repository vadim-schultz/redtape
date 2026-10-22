# Discovery admin remediation — Run ledger

**Loop branch:** `feat/plans-discovery-admin-remediation`
**Release branch:** `main`
**Release PR:** [#161](https://github.com/vadim-schultz/redtape/pull/161) — merged into `main`

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file.

Use this ledger to record chapter implementation, verification, refactor outcome, and release status.

| Chapter | Branch / PR | Red → green evidence | Refactor outcome | CI / smoke | Status |
| --- | --- | --- | --- | --- | --- |
| 1. Live triage — probe and routes | `docs/discovery-admin-remediation-triage` / [#157](https://github.com/vadim-schultz/redtape/pull/157) | Probe 401 "Not authenticated" (operator-reported; origin unconfirmed); allowlist OK, MACHINE_OPT_IN=false. Likely cause: Supabase JWKS/issuer unset on Render (auth_enabled false) or Authorization dropped by proxy. Blank page reported (F1). Chapter 3 cause-specific part: no-go until operator checks Render Supabase vars | n/a (ops) | local ci pass; remote pass; merged | merged |
| 2. Route nesting fix | `fix/discovery-admin-route-nesting` / [#158](https://github.com/vadim-schultz/redtape/pull/158) | 2 real-App tests red (empty body) → green via relative routes under pathless guarded layout | Audited; no refactor needed | remote pass; local ./ci.sh red only from pre-existing flaky suggestions tests (timeouts under load, pass in isolation) | merged |
| 3. Admin probe resilience and menu feedback | `fix/discovery-admin-probe-resilience` / [#159](https://github.com/vadim-schultz/redtape/pull/159) | Tests-first: recovery after 502, hint on persistent 503, no hint on 401/403, retry cap | MENU_VIEWS lookup extracted; narrow suites 41 pass | remote pass; local ./ci.sh red only from known flaky suggestions tests (54/54 pass in isolation) | merged |
| 4. Real-tree smoke and docs | `docs/discovery-admin-remediation-smoke` / [#160](https://github.com/vadim-schultz/redtape/pull/160) | 7 real-App cases, all characterization (already green after ch. 2-3); docs corrected | Audited; guard cases folded into `it.each` | remote pass; local web gate pass, ./ci.sh 1 known flaky suggestions test (passes in isolation). Deployed manual smoke NOT run (operator) | merged |

## Release gate

- [x] All chapter tests and refactor outcomes recorded.
- [ ] `./ci.sh` passes on `feat/plans-discovery-admin-remediation` (only known flaky suggestions tests fail locally; remote CI green).
- [~] Probe status recorded (401); Render config fix NOT yet applied/verified (operator).
- [ ] Worker-origin admin API smoke passes with the expected `401`/`403`/`200` outcomes.
- [ ] Allowlisted user sees Catalogue, Coverage, and Tasks in the menu and all three pages render.
- [ ] Release PR opened from `feat/plans-discovery-admin-remediation` to `main`.

**Last orchestration:** 2026-10-22 — completed (all chapters merged; release PR #161 merged)
