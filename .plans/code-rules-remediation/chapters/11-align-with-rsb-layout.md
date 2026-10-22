---
name: "Chapter 11 — Align with the rsb-test-storage layout"
overview: "Pure moves and barrels so every redtape feature follows the rsb-test-storage breakdown; central queryKeys, shared hooks, and a written convention."
todos:
  - id: shared-hooks
    content: "src/hooks with useSlowRequest, useLocalesQuery, and a useApiQuery wrapper"
    status: pending
  - id: query-keys
    content: "Central app/queryKeys.ts replaces inline query keys"
    status: pending
  - id: component-folders
    content: "<X>View/ folders with index.ts barrels, one feature per commit"
    status: pending
  - id: discovery-admin-layers
    content: "discovery-admin root files move into components, utils, and routes"
    status: pending
  - id: convention-doc
    content: "apps/web/CLAUDE.md documents the layout"
    status: pending
isProject: false
---

# Chapter 11 — Align with the rsb-test-storage layout

**Repo:** `redtape` · **Branch:** `refactor/align-rsb-layout` · **Status:** planned

**Depends on:** chapter 10 · **Architecture:** [../00-architecture.md](../00-architecture.md) F5 and §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

Make the redtape frontend feature breakdown match the sibling repo `/home/schult_v/projects/rsb-test-storage/frontend/src` (read it first; it is the reference). Moves and renames only: imports, barrels, and the shared hook and key registries. **No logic edits** in move commits (decision D10).

Reference summary: each feature has `containers/` (route pages), `components/` (presentational, `<X>View/{View,Header,Table,index.ts}` folders), `hooks/` (thin wrappers over a service and `queryKeys`), `services/` (`*Api.ts`), `types/`, `utils/`, and `registry/` only where a real plug-in point exists. Shared code is under `src/components`, `src/hooks`, and `src/app` (routes, queryClient, `queryKeys.ts`). Tests are co-located `X.test.tsx`.

All paths are under `apps/web/src` unless stated.

## Moves

1. **Shared hooks.** Create `hooks/`; move `components/feedback/useSlowRequest.ts` and `components/layout/useLocalesQuery.ts` (and their tests) there. Add a shared `useApiQuery` wrapper modelled on `rsb-test-storage/frontend/src/hooks/useApiQuery.ts`, then convert the feature `use*Query` hooks to thin wrappers over it.
2. **Central query keys.** Add `app/queryKeys.ts` with nested key factories (`queryKeys.documents.list(filters)`, and so on); replace the inline keys in all hooks and in `invalidateQueries` calls. Decision D6: this is the chapter that does it.
3. **Component folders.** Rename kebab-case component folders to PascalCase `<X>View/` folders with `index.ts` barrels (decision D4), one feature per commit: `documents` (`documents-list/`, `document-detail/`, `document-tags/`, `document-filters/`), `suggestions` (`suggest/`, `suggestions-list/`, `suggestion-detail/`), `locations` (`location-picker/`, `location-bar/`, `select-segment/`, `country-segment/`). Containers import the folder barrel. Keep tests beside their source.
4. **discovery-admin layers.** Move the feature-root files into layers: `DiscoveryAdminLayout.tsx` and `RequireDiscoveryAdmin.tsx` to `components/`, `discoveryAdminGuardOutcome.ts` and `discoveryAdminProbeErrors.ts` to `utils/`, `DiscoveryAdminTasksPlaceholder.tsx` to `components/` (or delete it if unused), `DiscoveryAdminRoutes.tsx` to one documented `routes.tsx` per decision in the PR. Keep `app/routes.tsx` mounting unchanged (see the discovery-admin-remediation suite: route tests must go through the real tree).
5. **Odd folders.** `features/locations/config/` to `utils/` (or `types/`); `features/taxonomy/hooks/staleTime.ts` (a constant, not a hook) to `utils/`; `src/views/` (`ForbiddenView`, `NotFoundView`) to `components/feedback/` or containers under `app/`; keep `contexts/` plural (D7).
6. **Registry (conditional).** Add a feature `registry/` only if there is a real plug-in point: a renderer map keyed by a type with three or more variants. Suggestion payload renderers (`new_document`, `new_requirement`, ...) are the candidate; today there are two, so skip unless a third exists. Record the decision in the PR.
7. **Convention doc.** Add `apps/web/CLAUDE.md` with the layer tree, import direction (container to components and hooks to services to types and utils), barrel policy, co-located tests, size limits (3 props, about 100 lines per file, about 5 lines per function), and the `queryKeys` and shared hook rules. Optionally add ESLint `no-restricted-imports` (components must not import `services/*`) and `max-lines` if they can be enabled without a flood of violations (open seam in the decisions file).

## TDD loop

This chapter is structural, so the safety net is the existing 336-test suite plus two guards that are new:

1. Happy path: an architecture test (or ESLint rule run as a test) proves components under `features/*/components` import nothing from `features/*/services`, and every query key comes from `queryKeys` (a grep-style test over the source tree).
2. Negative path: the test fails on a fixture violation (a component importing a service) so the guard is known to bite.

Red: write the guard first; it fails on the current tree. Green: do the moves until it passes. Run the full web suite after **each** feature's commit, never only at the end.

### Refactor

Check each moved folder against the checklist (barrel present, tests co-located, no file over about 100 lines, no leftover empty folders). Report: number of files moved, number of barrels added, inline query keys remaining (expected: 0), and the final `src/` tree for one feature as an example.

## Verification

```bash
cd apps/web
npm run test
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
git log --follow --oneline apps/web/src/features/documents/components/DocumentsListView/DocumentsListView.tsx | head
```

The last command confirms history follows the rename.

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/align-rsb-layout
```

```text
test(web): guard layer imports and central query keys
refactor(web): add shared hooks and central query keys
refactor(web): move documents components into <X>View folders with barrels
refactor(web): move suggestions components into <X>View folders with barrels
refactor(web): move locations components into <X>View folders with barrels
refactor(web): move discovery-admin root files into layers
docs(web): document the feature layout in apps/web/CLAUDE.md
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`. If it is too large to review, split by feature into several PRs against the loop branch.
