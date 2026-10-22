---
name: "Chapter 2 — Route nesting fix"
overview: "Make DiscoveryAdminRoutes relative to the /admin/discovery/* mount so the admin pages render, proven through the real App route tree."
todos:
  - id: nesting-red
    content: "Real-tree tests: coverage page renders, unknown path shows not-found"
    status: pending
  - id: nesting-green
    content: "Pathless guarded layout route with relative children"
    status: pending
  - id: nesting-refactor
    content: "Audit DiscoveryAdminRoutes and remount the old route tests via the splat parent"
    status: pending
isProject: false
---

# Chapter 2 — Route nesting fix

**Repo:** `redtape` (`apps/web`) · **Branch:** `fix/discovery-admin-route-nesting` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §2 F1–F2, §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-remediation` · **Release branch:** `main`

## Goal

Every `/admin/discovery/*` URL renders content (or a deliberate state) in the real app. Today the descendant `<Routes>` in `DiscoveryAdminRoutes.tsx` declares the absolute `path="/admin/discovery"`; under the splat mount in `routes.tsx` the remaining path is `/catalogue`, so nothing matches and the body is `null`.

## Design decisions

Follow D1 and D6. Keep `routes.tsx` unchanged (its `/admin/discovery/*` mount is correct). Make the guarded layout a **pathless** route and the children relative. The index redirect `<Navigate to="catalogue" replace />` resolves against the splat base, so `/admin/discovery` still redirects.

```tsx
<Routes>
  <Route element={<RequireDiscoveryAdmin><DiscoveryAdminLayout /></RequireDiscoveryAdmin>}>
    <Route index element={<Navigate to="catalogue" replace />} />
    <Route path="catalogue" element={<DiscoveryCataloguePage />} />
    <Route path="coverage" element={<DiscoveryCoveragePage />} />
    <Route path="tasks" element={<DiscoveryTasksPage />} />
    <Route path="pipeline/:id" element={<DiscoveryPipelinePage />} />
    <Route path="*" element={<NotFoundView />} />
  </Route>
</Routes>
```

## Files

**Add or edit**

- `apps/web/src/app/routes.discoveryAdmin.test.tsx` (new) — real `App` inside `AppLayout` via `renderWithProviders`, same helper shape as `App.test.tsx`
- `apps/web/src/features/discovery-admin/DiscoveryAdminRoutes.tsx`
- `apps/web/src/features/discovery-admin/DiscoveryAdminRoutes.test.tsx` — mount through `<Routes><Route path="/admin/discovery/*" element={<DiscoveryAdminRoutes />} /></Routes>`

Reuse: `renderWithProviders`, `createFakeAuthGateway`, and the fetch stub from `DiscoveryAdminRoutes.test.tsx` (`/me`, `tasks`, `coverage`).

## TDD loop

### Red

1. `app · renders the discovery coverage page at /admin/discovery/coverage` — happy path. Authenticated fake session, stubbed `/me`, `tasks` (probe), `coverage`; assert the `govdata: 3` chip.
2. `app · renders not-found for an unknown discovery path` — negative path. `/admin/discovery/unknown` shows the "Page not found" heading, not an empty `main`.

Run `npm run test -- src/app/routes.discoveryAdmin.test.tsx` and confirm **both fail for the right reason** (the body is empty), not for setup errors. If either passes, stop and re-diagnose with the chapter 1 note.

### Green

1. Replace the absolute-path route with the pathless guarded layout route shown above.
2. Remount the existing `DiscoveryAdminRoutes.test.tsx` cases through the splat parent so they match production.
3. Both new tests and the existing route/guard tests pass.

### Refactor

Audit the whole `DiscoveryAdminRoutes` entity per the refactor-step checklist: dispatch-only, about 20 lines, one concern, no boolean parameters, one nesting level. Confirm `RequireDiscoveryAdmin` and `DiscoveryAdminLayout` need no change. Expected outcome: "no refactor needed" — report it explicitly. Re-run the narrow suite.

## Verification

```bash
cd apps/web
npm run test -- src/app/routes.discoveryAdmin.test.tsx src/features/discovery-admin
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

Compare failures of the full web suite with the baseline recorded before this chapter; report any difference.

## Git workflow

```bash
git checkout feat/plans-discovery-admin-remediation && git pull
git checkout -b fix/discovery-admin-route-nesting
```

```text
test(web): cover discovery admin routes through the app tree
fix(web): make discovery admin routes relative to the splat mount
```

Open the chapter PR into `feat/plans-discovery-admin-remediation`, not `main`.
