---
name: Discovery admin remediation — Gaps and decisions
overview: "Settled route, guard, probe-retry, and menu-feedback decisions for the discovery admin remediation."
isProject: false
---

# Discovery admin remediation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | Descendant `<Routes>` under the `/admin/discovery/*` mount use **relative** paths. The guarded layout is a pathless route; `routes.tsx` keeps its splat mount. |
| D2 | **Both admin guards stay** (web `RequireDiscoveryAdmin`, API `require_discovery_admin`). A temporary bypass is not part of this suite; removing the web guard would not show data and removing the API guard is a security-relevant change. Chapter 1 isolates the guard question with a local run using `DISCOVERY_ADMIN_EMAILS=<operator email>`. |
| D3 | Triage (chapter 1) precedes menu code. Chapter 3's cause-specific follow-up follows the recorded finding; Render configuration fixes are operator actions recorded in the ledger. |
| D4 | The admin probe uses the shared `shouldRetry`/`retryDelay` from `apps/web/src/app/retryPolicy.ts` (retry 5xx and network errors, never 4xx), **capped at 2 retries** so a truly disabled discovery does not wait about 23 s. |
| D5 | The menu hides links on 401/403 (identical to a non-admin, by design) and shows a muted, non-link "Discovery unavailable" hint for 503/5xx/network after retries. |
| D6 | Route and menu tests go through `App` or a parent splat route, never the nested component alone. |
| D7 | Reuse `useDiscoveryAdminProbe`, `discoveryAdminProbeErrors.ts`, `retryPolicy.ts`, `renderWithProviders`, and `createFakeAuthGateway`. No new dependency. |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| Distinct "not on allowlist" hint for admins | Needs a server signal; the API returns a plain 403 today. |
| Extract the 7-arm `renderGuardOutcome` switch | The next change that touches `RequireDiscoveryAdmin.tsx`. |
| Dedicated loading state for `DiscoveryCoveragePage` | Cosmetic; do it when the page next changes. |

## Out of scope

Backend routes, schemas, migrations, ingest workers, Supabase provider changes, a client-side email list, and removal of any guard.
