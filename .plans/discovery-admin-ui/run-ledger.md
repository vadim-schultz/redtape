# Discovery admin UI — Run ledger

**Loop branch:** `feat/plans-discovery-admin-ui`
**Release branch:** `main`
**Release PR:** _(filled when opened)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file.

Use this ledger to record chapter implementation, verification, refactor outcome, and release status.

| Chapter | Branch / PR | Red → green evidence | Refactor outcome | CI / smoke | Status |
| --- | --- | --- | --- | --- | --- |
| 1. Route contract and coverage | — | — | — | — | planned |
| 2. Admin guard feedback | — | — | — | — | planned |
| 3. Catalogue data states | — | — | — | — | planned |
| 4. Menu discovery navigation | — | — | — | — | planned |
| 5. Integration smoke and docs | — | — | — | — | planned |

## Release gate

- [ ] All chapter tests and refactor outcomes recorded.
- [ ] `./ci.sh` passes on `feat/plans-discovery-admin-ui`.
- [ ] Render health returns application JSON.
- [ ] Worker-origin admin API smoke passes with the expected `401`/`403`/`200` outcomes.
- [ ] Allowlisted user sees the documented admin routes and menu links.
- [ ] Release PR opened from `feat/plans-discovery-admin-ui` to `main`.

**Last orchestration:** 2026-10-21 — stopped at chapter 1: Docker daemon unavailable and Vitest fork permissions blocked the required CI gate.
