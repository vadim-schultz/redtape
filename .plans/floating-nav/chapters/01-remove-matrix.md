---
name: "Chapter 1 — Remove matrix"
overview: "Remove the /matrix route, nav link, matrix components, matrix query hook, axis/cell utils, matrix API client function and matrix.* / nav.matrix i18n keys. Domain and life-situation filters stay the only taxonomy entry point."
todos:
  - id: route
    content: "Drop /matrix route; unknown path shows NotFoundView"
    status: pending
  - id: nav
    content: "Remove the matrix link from AppLayout (and its test)"
    status: pending
  - id: code
    content: "Delete MatrixPage, components/matrix/*, useMatrixQuery, buildAxis, buildCellIndex, matrix client fn and their tests"
    status: pending
  - id: i18n
    content: "Remove nav.matrix and matrix.* from all four bundles"
    status: pending
isProject: false
---

# Chapter 1 — Remove matrix

**Repo:** `redtape` (`apps/web`, `apps/api` seed data) · **Branch:** `feat/floating-nav-remove-matrix` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The matrix page is confusing for an average user. Remove it so the domain / life-situation chips on the
documents list are the single, clear way to browse by taxonomy.

## Design decisions

**Delete, don't hide.** Dead code and unreachable routes rot; git history keeps the matrix (D1).

**Keep shared pieces.** `useDomainsQuery`, `useLifeSituationsQuery`, `DocumentFilters`, `TagBadge` and
`buildDocumentsHref` are used by the list and detail pages and stay. Before deleting a util or hook,
grep for other importers.

**i18n parity.** The fallback test compares web bundles with the API seed files, so keys are removed from
`apps/web/src/i18n/fallback/{en,de}.json` **and** `apps/api/scripts/seed_data/translations/{en,de}.json`
in the same commit.

**Backend untouched.** The matrix endpoint stays, dormant (see [gaps](../gaps-and-decisions.md)).

## Files

**Delete** — `apps/web/src/features/taxonomy/containers/MatrixPage.tsx` (+ test),
`features/taxonomy/components/matrix/*` (+ tests, `fixtures.ts`), `hooks/useMatrixQuery.ts`,
`utils/buildAxis.ts`, `utils/buildCellIndex.ts` (+ tests), the matrix function in `services/taxonomyApi.ts`
(+ its test cases), matrix types no longer referenced.

**Edit** — [routes.tsx](../../../apps/web/src/app/routes.tsx),
[AppLayout.tsx](../../../apps/web/src/components/layout/AppLayout.tsx) and its test, the four translation
JSON files.

## Red tests

| Test | Asserts |
| --- | --- |
| `routes · /matrix shows NotFoundView` | Removed route falls through to not-found |
| `routes · /documents and /documents/:id still resolve` | Regression, negative side of the removal |
| `AppLayout · has no matrix link` | Nav no longer links to `/matrix` |
| `fallback · en and de bundles have no matrix or nav.matrix keys` | Keys removed and still equal to API seed |
| `taxonomyApi · domains and situations clients still work` | Kept clients untouched |

## Green

1. Write the failing route and nav tests, then remove the route and link.
2. Delete the matrix code and tests; run typecheck to find leftovers.
3. Remove i18n keys in all four files; parity test stays green.

## Refactor gate

Grep confirms no reference to `matrix`, `Matrix` remains in `apps/web/src` except historical docs. No
methods over ~5 LOC introduced.

## Verification

`npm run test`, `npm run lint && npm run format:check && npm run typecheck && npm run build`, `./ci.sh`.
Manual: `/matrix` shows not-found; list filters still work.

## Out of scope

Deleting the backend endpoint; new nav (chapter 5).

## Git workflow

Branch `feat/floating-nav-remove-matrix`; `test(web): describe matrix removal`, then
`feat(web): remove matrix view`; one PR.
