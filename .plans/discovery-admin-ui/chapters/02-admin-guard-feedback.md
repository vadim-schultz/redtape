---
name: "Chapter 2 — Admin guard feedback"
overview: "Replace silent auth, probe, lazy-route, and disabled-discovery waits with visible, actionable feedback."
todos:
  - id: guard-red
    content: "Add paired guard tests for allow and visible wait/error states"
    status: pending
  - id: guard-green
    content: "Implement loading, unconfigured, and 503 feedback"
    status: pending
  - id: guard-refactor
    content: "Audit guard decision branches and shared feedback components"
    status: pending
isProject: false
---

# Chapter 2 — Admin guard feedback

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/discovery-admin-ui-guard-feedback` · **Status:** planned

**Depends on:** [01](01-route-contract-and-coverage.md) merged · **Architecture:** [../00-architecture.md](../00-architecture.md) §3–5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-ui` · **Release branch:** `main`

## Goal

Ensure the shared `RequireDiscoveryAdmin` gate never turns a valid admin URL into a silent blank while
auth, the server probe, or the lazy discovery route is unresolved.

Current behavior to remediate:

- `RequireDiscoveryAdmin.tsx` returns `null` for `wait`.
- `discoveryAdminGuardOutcome.ts` treats `unconfigured` auth as an indefinite wait.
- `routes.tsx` and `App.tsx` use `fallback={null}` around lazy route loading.
- API `503` is currently a generic error instead of an actionable “discovery disabled” state.

## Design decisions

Keep the decision function pure and keep view markup in named components. Reuse the existing
`QueryError` and `EmptyStateCard` patterns; add a small `DiscoveryAdminLoading` and
`DiscoveryAdminDisabled` only if the existing components cannot express the required copy and retry
behavior.

Preserve existing outcomes:

- authenticated allowlisted user → children;
- `401` → login;
- `403` → `ForbiddenView`;
- transient/API failure → retryable error;
- `503` → explicit discovery configuration/disabled feedback.

## Files

**Add or edit**

- `apps/web/src/features/discovery-admin/RequireDiscoveryAdmin.tsx`
- `apps/web/src/features/discovery-admin/discoveryAdminGuardOutcome.ts`
- `apps/web/src/features/discovery-admin/discoveryAdminProbeErrors.ts`
- `apps/web/src/features/discovery-admin/components/DiscoveryAdminLoading.tsx`
- `apps/web/src/features/discovery-admin/components/DiscoveryAdminDisabled.tsx`
- `apps/web/src/features/discovery-admin/RequireDiscoveryAdmin.test.tsx`
- `apps/web/src/app/routes.tsx` and `apps/web/src/app/App.tsx` lazy fallbacks
- locale fallback keys only if new feedback copy is needed

## TDD loop

### Red

1. `RequireDiscoveryAdmin · renders children when the allowlisted probe returns 200` — happy path;
   preserve the existing success contract.
2. `RequireDiscoveryAdmin · renders visible feedback while the probe is loading` — negative/wait
   path; assert no blank content.
3. `RequireDiscoveryAdmin · renders an auth configuration message when Supabase is unconfigured` —
   negative/configuration path; assert the state does not wait forever.
4. `RequireDiscoveryAdmin · explains discovery is disabled for a 503 probe` — negative/backend
   feature-gate path; assert actionable feedback and retry behavior.

Run the guard suite and confirm each new assertion fails against the current `return null`/generic
error behavior.

### Green

1. Add explicit guard outcomes for transient loading, unconfigured auth, and disabled discovery while
   retaining the existing login/forbidden/error outcomes.
2. Render a visible loading shell from the guard.
3. Map `ApiRequestError.status === 503` to the disabled view.
4. Replace discovery lazy-route `fallback={null}` with the same or a compatible visible loading shell.
5. Keep retry handlers connected to the existing React Query probe.

### Refactor

Audit the full guard and outcome function, not only new lines:

- the decision has no more than two branches per variant family without named dispatch;
- auth decision logic is not mixed with JSX layout;
- 401/403/503 error mapping is not duplicated;
- loading and disabled views have one concern each;
- no boolean parameter is threaded to select guard behavior.

Rerun `RequireDiscoveryAdmin.test.tsx` after each extraction and report the refactor outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin/RequireDiscoveryAdmin.test.tsx
npm run test -- src/app
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-discovery-admin-ui && git pull
git checkout -b feat/discovery-admin-ui-guard-feedback
```

```text
test(web): cover discovery admin loading and disabled states
fix(web): show discovery admin guard feedback
```

Open the chapter PR into `feat/plans-discovery-admin-ui`, not `main`.
