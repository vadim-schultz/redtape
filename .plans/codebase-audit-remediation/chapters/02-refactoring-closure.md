---
name: "Chapter 2 — Refactoring closure"
overview: "Give discovery-admin prefetch and hooks one query-options source of truth, remove the duplicate CompletenessChips tree, and move shared artifact timing to a neutral constants module."
todos:
  - id: query-options
    content: "Characterize and centralize the five secondary query-options factories."
    status: pending
  - id: completeness-tree
    content: "Confirm the feature-local CompletenessChips tree is unused and remove it."
    status: pending
  - id: timing-constant
    content: "Move ARTIFACT_STALE_MS out of a hook module and verify both artifact paths use it."
    status: pending
isProject: false
---

# Chapter 2 — Refactoring closure

**Repo:** `redtape` · **Branch:** `refactor/audit-remediation-web` · **Status:** planned  
**Depends on:** parent audit on `main` · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit-remediation` · **Release branch:** `main`

## Goal

Complete two refactors that the parent W2/W4 work left partially duplicated:

- one typed `queryOptions` factory per secondary discovery-admin resource, used by both its hook
  and `sectionPrefetch.ts`;
- one `CompletenessChips` tree under shared data-display code.

Move the artifact stale-time constant to a neutral query-timing module so prefetch code does not
depend on a hook module.

## Design decisions

- Colocate each factory with the hook that owns the resource. Prefetch imports the factory; hooks
  do not import the prefetch module.
- Factories accept the existing `AdminAuth` plus the resource identifier and include all query
  options that affect cache behavior.
- Delete the feature-local component tree after a repository-wide import search. Do not leave a
  compatibility re-export that preserves two ownership paths.
- Keep query keys, fetch functions, stale time, and refetch behavior unchanged.

## Files

| Path | Change |
| --- | --- |
| `apps/web/src/features/discovery-admin/hooks/use*Query.ts` | Export and consume resource query-options factories. |
| `apps/web/src/features/discovery-admin/containers/sectionPrefetch.ts` | Call the shared factories only. |
| `apps/web/src/features/discovery-admin/constants/queryTiming.ts` | Own `ARTIFACT_STALE_MS`. |
| `apps/web/src/features/discovery-admin/hooks/useDiscoveryArtifactsQuery.ts` | Import timing from the neutral module. |
| `apps/web/src/components/data-display/CompletenessChips/` | Keep the single shared implementation. |
| `apps/web/src/features/candidates/components/CompletenessChips/` | Delete the duplicate tree and tests after proving it is unused. |
| `apps/web/src/architecture.test.ts` or the ESLint baseline | Remove only stale duplicate-path entries, if any. |

Do not change presentational panel behavior, API services, query-key shapes, or the parent audit
ledger in this chapter.

## Red tests and characterization

This is a behavior-preserving refactor. Keep existing happy-path and negative-path tests green,
and add only characterization needed to prevent drift before moving code:

- Happy: the candidate edges, candidate artifacts, candidate emit-preview, catalogue artifacts,
  and catalogue preview hooks still load their current responses.
- Negative: an artifact query still uses the four-minute stale time and refetch-on-focus behavior;
  prefetch and hook use the same query-key/options factory rather than two independently assembled
  definitions.
- Happy: shared `CompletenessChips` renders the existing flags and orientation.
- Negative: no production import or tracked source path refers to
  `features/candidates/components/CompletenessChips`.

The negative checks should fail before the refactor because the duplicate tree and inline prefetch
definitions are present. Do not add new behavior during the refactor phase.

## Green

1. Move `ARTIFACT_STALE_MS` into `constants/queryTiming.ts`.
2. Export one factory from each secondary query hook and replace the corresponding inline
   `queryOptions` in `sectionPrefetch.ts`.
3. Run the existing discovery-admin and shared component suites.
4. Remove the feature-local `CompletenessChips` directory and stale architecture entry only after
   the import search is clean.

## Refactor gate

Audit every touched hook and `sectionPrefetch.ts`:

- inline `queryOptions({ ... })` definitions in `sectionPrefetch.ts`: `5 → 0`;
- factory definitions per secondary resource: `2 → 1`;
- `ARTIFACT_STALE_MS` export location: hook module → neutral constants module;
- `CompletenessChips` implementation trees: `2 → 1`;
- no one-line wrapper remains whose only purpose is to forward the same options to another
  function.

Report `Refactor gate: smells found -> duplicated query options, duplicate component tree, and
misplaced timing constant; refactorings applied -> ...`. Re-run the narrow suite after each
extraction and explicitly report no further refactor when the containing entities are single
concern.

## Verification

```bash
cd apps/web
npx tsc --noEmit
npx eslint "src/features/discovery-admin/**/*.{ts,tsx}"
npm test -- src/features/discovery-admin src/components/data-display/CompletenessChips src/architecture.test.ts
! rg 'queryOptions\(' src/features/discovery-admin/containers/sectionPrefetch.ts
! rg 'features/candidates/components/CompletenessChips' src
```

Run `./ci.sh` before the chapter PR is pushed.

## Out of scope

New section containers, API or ingest changes, enum-label changes, unrelated query-status
wrappers, and unresolved T3 layout exceptions.

## Git workflow

```bash
git checkout feat/plans-codebase-audit-remediation && git pull
git checkout -b refactor/audit-remediation-web
```

Use `refactor(web): ...` and `chore(web): ...` conventional commits. Open the chapter PR into the
remediation loop branch, not `main`.

