---
name: "Chapter 4 — Admin shell + email gate"
overview: "Admin layout under /admin/discovery with route guard; non-allowlisted users see forbidden state."
todos:
  - id: routes
    content: "React routes + DiscoveryAdminLayout"
    status: pending
  - id: guard
    content: "RequireDiscoveryAdmin wrapper using /me + allowlist config"
    status: pending
isProject: false
---

# Chapter 4 — Admin shell + email gate

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/discovery-layer-admin-shell` · **Status:** planned

**Depends on:** [2](02-admin-discovery-api.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §9 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

`/admin/discovery/*` routes exist behind authentication. Allowlisted emails see a minimal admin shell;
others see the existing forbidden pattern.

## Design decisions

**Allowlist** is enforced server-side (chapter 2); web guard calls admin API health/list and maps 403 to
`ForbiddenView` — do not embed emails in the web bundle.

**No public nav link** to admin (D1).

**Layout:** page title + outlet for chapters 5–7.

## Files

| Path | Change |
| --- | --- |
| `apps/web/src/features/discovery-admin/` | `DiscoveryAdminLayout.tsx`, `RequireDiscoveryAdmin.tsx`, routes |
| `apps/web/src/app/` | Register admin routes |
| `apps/web/src/features/discovery-admin/RequireDiscoveryAdmin.test.tsx` | Tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `RequireDiscoveryAdmin · renders children when admin API returns 200` | Happy path |
| `RequireDiscoveryAdmin · renders forbidden when admin API returns 403` | Negative |
| `RequireDiscoveryAdmin · redirects or shows login when unauthenticated` | Negative |

## Green

1. Route registration + layout shell.
2. Guard component with mocked API client; tests 1–3.

## Refactor gate

Guard is one concern; layout separate. Report outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin/RequireDiscoveryAdmin.test.tsx
cd ../.. && ./ci.sh
```

## Out of scope

Task table data (chapter 5), catalogue index UI.

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-admin-shell
```

```text
test(web): discovery admin route guard

feat(web): add discovery admin shell and email gate
```

Open PR into `feat/plans-discovery-layer`.
