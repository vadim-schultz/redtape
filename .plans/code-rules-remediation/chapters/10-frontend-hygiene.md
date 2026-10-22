---
name: "Chapter 10 — Frontend hygiene"
overview: "Delete the stray draft file and untangle DiscoveryCataloguePage; moves into the rsb layout stay in chapter 11."
todos:
  - id: delete-draft
    content: "Remove the tracked LocaleContext.tsx.draft"
    status: pending
  - id: catalogue-state
    content: "useCatalogueState extracted from DiscoveryCataloguePage"
    status: pending
  - id: pipeline-page
    content: "DiscoveryPipelinePage inline branches extracted"
    status: pending
isProject: false
---

# Chapter 10 — Frontend hygiene

**Repo:** `redtape` · **Branch:** `refactor/frontend-hygiene` · **Status:** planned

**Depends on:** chapter 9 · **Architecture:** [../00-architecture.md](../00-architecture.md) F4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

Small clean-ups that are not folder moves (those are chapter 11): remove dead files and split the two discovery containers that mix concerns.

All paths are under `apps/web/src`.

## Files

- `contexts/LocaleContext.tsx.draft` (83 lines) — stray, committed. Confirm it is unreferenced (`grep`), then delete.
- `features/discovery-admin/containers/DiscoveryCataloguePage.tsx` (73 lines) — two queries, the state function `queryStateFor` (3 positional parameters, line 12), both-loading and both-error branching, two panels, and a non-null assertion `coverageQuery.data!` (line 63). Extract a `useCatalogueState` hook that returns one typed state (a discriminated union), and render with a dispatch-only mapping.
- `features/discovery-admin/containers/DiscoveryPipelinePage.tsx` (54 lines) — inline rendering branches; extract the branches to named components or a dispatch map.
- `features/discovery-admin/containers/DiscoveryCoveragePage.tsx` — uses plain `<Text>` for loading instead of `DiscoveryAdminLoading` (noted in the discovery-admin-remediation suite as cosmetic, do it now since the file is touched; skip if the file does not change).
- `features/discovery-admin/RequireDiscoveryAdmin.tsx` — the 7-arm `renderGuardOutcome` `switch`: this is rule of three (more than 2 arms). Extract a lookup of outcome to renderer, as `AppMenu` did with `MENU_VIEWS`.
- Tests: `DiscoveryCataloguePage.test.tsx`, `DiscoveryPipelinePage.test.tsx`, `RequireDiscoveryAdmin.test.tsx`.

## TDD loop

### Red

1. `useCatalogueState` happy path: both queries succeeded gives state `ready` with rows and coverage; coverage failed but catalogue succeeded gives `ready` with rows and a coverage error flag (existing behaviour "keeps catalogue rows visible when coverage fails").
2. `useCatalogueState` negative path: catalogue failed gives `error` with a retry; both loading gives `loading`; never a non-null assertion on undefined data.
3. Guard outcomes: each of the 7 outcomes renders the right view (characterization, parametrised with `it.each`); an unknown outcome is a type error, not a runtime fallthrough.

### Green

1. Delete the draft file.
2. Extract `useCatalogueState` and the dispatch mapping; remove the `!` assertion.
3. Replace the `renderGuardOutcome` switch with a typed lookup.
4. Extract the pipeline page's branches.

### Refactor

Audit the three containers and the guard: at most 3 props or parameters, dispatch-only mappings, about 5 lines per function, one nesting level. Report file line counts before and after.

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin src/contexts
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/frontend-hygiene
```

```text
test(web): pin catalogue state and guard outcome rendering
refactor(web): extract catalogue state, dispatch guard outcomes, and drop the stray draft
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`.
