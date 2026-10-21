---
name: "Chapter 3 — Catalogue data states"
overview: "Make catalogue and coverage queries independently visible, retryable, and useful when discovery data is empty or partially available."
todos:
  - id: catalogue-red
    content: "Add catalogue happy and query-failure tests"
    status: pending
  - id: catalogue-green
    content: "Implement independent catalogue and coverage states"
    status: pending
  - id: catalogue-refactor
    content: "Audit page orchestration and status-component boundaries"
    status: pending
isProject: false
---

# Chapter 3 — Catalogue data states

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/discovery-admin-ui-catalogue-states` · **Status:** planned

**Depends on:** [02](02-admin-guard-feedback.md) merged · **Architecture:** [../00-architecture.md](../00-architecture.md) §3–5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-ui` · **Release branch:** `main`

## Goal

Make `/admin/discovery/catalogue` explain what is happening at the query layer. The catalogue request
and coverage request currently run in parallel, but any error collapses the page to one generic text
message. A successful catalogue response must remain useful when only the summary request fails.

## Design decisions

Keep `DiscoveryCataloguePage` as the container. Reuse:

- `useDiscoveryCatalogueQuery`;
- `useDiscoveryCoverageQuery`;
- `CatalogueServicesTable`;
- `CoverageChips`;
- `QueryError` and existing empty-state patterns.

Do not move API calls into table or chip components. Do not alter the backend response DTOs.

Expected states:

- both queries loading → visible page loading state;
- catalogue success + coverage success → chips and rows;
- catalogue success + empty items → existing empty table message plus coverage;
- catalogue failure → catalogue retry state;
- coverage failure + catalogue success → rows remain visible and coverage retry state appears;
- both fail → a clear combined or primary retry state.

## Files

**Add or edit**

- `apps/web/src/features/discovery-admin/containers/DiscoveryCataloguePage.tsx`
- A focused catalogue status component only if the page repeats a non-trivial state
- `apps/web/src/features/discovery-admin/containers/DiscoveryCataloguePage.test.tsx`
- Existing table/status tests if assertions move to a reusable component

## TDD loop

### Red

1. `DiscoveryCataloguePage · renders coverage chips and catalogue rows after both requests succeed` —
   happy path; assert a seeded row and coverage counts are visible.
2. `DiscoveryCataloguePage · keeps catalogue rows visible when coverage fails` — negative/partial
   failure path; assert the row remains and a coverage retry/error state is visible.
3. `DiscoveryCataloguePage · shows a retryable state when catalogue loading fails` —
   negative/primary failure path; assert the existing retry affordance is visible.
4. `DiscoveryCataloguePage · shows a deliberate empty state for zero catalogue rows` — negative/data
   boundary; assert the page is not blank when the database has no catalogue rows.

Run the focused page suite and confirm the tests fail against the current all-or-nothing error branch
and missing page test.

### Green

1. Separate catalogue and coverage loading/error presentation while retaining the existing query
   hooks.
2. Preserve `CoverageChips` when coverage succeeds.
3. Preserve `CatalogueServicesTable` and its empty state when catalogue succeeds with zero rows.
4. Attach retry handlers to the failing query without invalidating unrelated successful data.

### Refactor

Audit the entire `DiscoveryCataloguePage` and any extracted status component:

- page code remains orchestration, not table/chip rendering;
- loading/error branches are named and shallow;
- no repeated error mapping or boolean mode parameter appears;
- the two query results are not threaded as an unstructured data clump across components;
- the containing component remains one concern.

Rerun the focused catalogue suite after each extraction and report the refactor outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin/containers/DiscoveryCataloguePage.test.tsx
npm run test -- src/features/discovery-admin
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-discovery-admin-ui && git pull
git checkout -b feat/discovery-admin-ui-catalogue-states
```

```text
test(web): cover discovery catalogue query states
fix(web): keep catalogue data visible during coverage failures
```

Open the chapter PR into `feat/plans-discovery-admin-ui`, not `main`.
