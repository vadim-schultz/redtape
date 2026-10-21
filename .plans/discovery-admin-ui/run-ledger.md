# Discovery admin UI — Run ledger

**Loop branch:** `feat/plans-discovery-admin-ui`
**Release branch:** `main`
**Release PR:** _(filled when opened)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file.

Use this ledger to record chapter implementation, verification, refactor outcome, and release status.

| Chapter | Branch / PR | Red → green evidence | Refactor outcome | CI / smoke | Status |
| --- | --- | --- | --- | --- | --- |
| 1. Route contract and coverage | `feat/discovery-admin-ui-route-contract` / [PR #150](https://github.com/vadim-schultz/redtape/pull/150) | Happy coverage route, unknown-path fallback, and coverage error/retry tests passed | Dispatch-only routes; reused `CoverageChips` and `QueryError` | Non-Docker checks passed; Docker/Postgres checks skipped; remote checks passed | merged |
| 2. Admin guard feedback | `feat/discovery-admin-ui-guard-feedback` / [PR #151](https://github.com/vadim-schultz/redtape/pull/151) | Allow, loading, unconfigured-auth, and 503-disabled tests passed | Pure guard; centralized error mapping; focused feedback components; no boolean mode switch | Chapter/app checks and remote checks passed; Docker checks skipped; 10 unrelated full-web failures remain | merged |
| 3. Catalogue data states | `feat/discovery-admin-ui-catalogue-states` / [PR #152](https://github.com/vadim-schultz/redtape/pull/152) | Both-success, coverage-failure with rows retained, catalogue failure, and empty-state tests passed | Independent query states; shallow orchestration; focused status boundaries | Non-Docker checks and remote checks passed; Docker/Postgres checks skipped | merged |
| 4. Menu discovery navigation | `feat/discovery-admin-ui-menu-navigation` / [PR #153](https://github.com/vadim-schultz/redtape/pull/153) | Allowlisted links, non-admin absence, icon labels/routes, Home ordering, and probe-failure resilience tests passed | Menu boundaries audited; no extraction needed | Non-Docker checks and remote checks passed; Docker/Postgres checks skipped | merged |
| 5. Integration smoke and docs | — | — | — | — | planned |

## Release gate

- [ ] All chapter tests and refactor outcomes recorded.
- [ ] `./ci.sh` passes on `feat/plans-discovery-admin-ui`.
- [ ] Render health returns application JSON.
- [ ] Worker-origin admin API smoke passes with the expected `401`/`403`/`200` outcomes.
- [ ] Allowlisted user sees the documented admin routes and menu links.
- [ ] Release PR opened from `feat/plans-discovery-admin-ui` to `main`.

**Last orchestration:** 2026-10-21 — chapter 4 merged; continuing at chapter 5.
