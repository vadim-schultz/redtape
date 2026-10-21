---
name: "Chapter 1 — Route contract and coverage page"
overview: "Register every discovery admin web route, add a dedicated coverage page, and prevent unmatched discovery paths from rendering an empty outlet."
todos:
  - id: route-red
    content: "Add full-route happy and unmatched-route negative tests"
    status: pending
  - id: coverage-green
    content: "Implement DiscoveryCoveragePage and route fallback"
    status: pending
  - id: route-refactor
    content: "Audit route dispatch and rerun narrow tests after each extraction"
    status: pending
isProject: false
---

# Chapter 1 — Route contract and coverage page

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/discovery-admin-ui-route-contract` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §2–3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-ui` · **Release branch:** `main`

## Goal

Make the intended discovery web surface explicit:

- `/admin/discovery` redirects to `/catalogue`.
- `/admin/discovery/catalogue`, `/tasks`, `/coverage`, and `/pipeline/:id` dispatch to a page.
- An unknown discovery child path has a deliberate fallback and never leaves `Outlet` empty.

## Design decisions

`DiscoveryCoveragePage` is a container because it owns the coverage query's loading/error/success
orchestration. It reuses `CoverageChips` for the actual summary presentation. No new API function or
response type is introduced.

Keep the current feature boundary in
[`apps/web/src/features/discovery-admin/`](../../../apps/web/src/features/discovery-admin/):
routes dispatch, containers orchestrate, components present.

## Files

**Add**

- `apps/web/src/features/discovery-admin/containers/DiscoveryCoveragePage.tsx`
- A route-level test under `apps/web/src/features/discovery-admin/`

**Edit**

- `apps/web/src/features/discovery-admin/DiscoveryAdminRoutes.tsx`
- Existing route/container test fixtures as required

## TDD loop

### Red

1. `DiscoveryAdminRoutes · renders the coverage page at /admin/discovery/coverage` — happy path;
   assert the coverage view appears after the mocked coverage request succeeds.
2. `DiscoveryAdminRoutes · renders a fallback for an unknown discovery path` — negative path; assert
   a deliberate redirect or not-found state, never an empty route outlet.
3. `DiscoveryCoveragePage · shows an error and retry action when coverage fails` — negative path;
   assert the existing retry/error pattern is visible.

Run the narrow route tests and confirm the new tests fail because the coverage route/page and fallback
are absent.

### Green

1. Add `DiscoveryCoveragePage` using `useDiscoveryCoverageQuery`.
2. Render visible loading feedback, `QueryError` with retry, and `CoverageChips` on success.
3. Register the `coverage` route and an explicit catch-all route in
   `DiscoveryAdminRoutes.tsx`.
4. Keep the existing index redirect and the pipeline/emit-preview route behavior unchanged.

### Refactor

Audit `DiscoveryAdminRoutes`, `DiscoveryCoveragePage`, and the route test harness:

- route arms only dispatch to named containers;
- no route branch contains query or presentation logic;
- no duplicated coverage formatting replaces `CoverageChips`;
- the containing route component has no silent branch or unnecessary nesting.

Rerun the narrow suite after each extraction or route change and report the refactor outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-discovery-admin-ui && git pull
git checkout -b feat/discovery-admin-ui-route-contract
```

```text
test(web): cover discovery admin route contract
feat(web): add discovery coverage route
```

Open the chapter PR into `feat/plans-discovery-admin-ui`, not `main`.
