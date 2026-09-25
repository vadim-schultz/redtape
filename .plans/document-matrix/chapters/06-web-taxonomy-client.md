---
name: "Chapter 6 — Web taxonomy client"
overview: "Typed API client, TanStack Query hooks and translation keys for domains, life situations and the matrix in apps/web; no visible UI yet."
todos:
  - id: types
    content: "Term, MatrixCell, MatrixResponse types"
    status: pending
  - id: client
    content: "taxonomyApi fetchers using apiRequest with locale"
    status: pending
  - id: hooks
    content: "useDomainsQuery, useLifeSituationsQuery, useMatrixQuery with locale in keys"
    status: pending
  - id: i18n
    content: "de/en keys for matrix and filter UI in API seeds and web fallback bundles"
    status: pending
isProject: false
---

# Chapter 6 — Web taxonomy client

**Repo:** `redtape` (`apps/web`, plus translation seeds in `apps/api`) · **Branch:** `feat/matrix-web-client` · **Status:** planned

**Depends on:** [3](03-taxonomy-api.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Components in later chapters can call `useDomainsQuery()`, `useLifeSituationsQuery()` and
`useMatrixQuery(scope)` and get typed, locale-aware data. All strings needed by chapters 7–9 exist in
both languages. Nothing renders differently.

## Design decisions

**New feature folder mirroring documents:** `apps/web/src/features/taxonomy/{services,hooks,types}`,
copying the shape of [documentsApi.ts](../../../apps/web/src/features/documents/services/documentsApi.ts)
and [useDocumentsListQuery.ts](../../../apps/web/src/features/documents/hooks/useDocumentsListQuery.ts).

**Locale in query keys** (`["domains", locale]`) so switching language refetches, as documents do.

**Taxonomy is long-lived data:** `staleTime` of several minutes; the lists change only on reseed.
Matrix query key includes the municipality scope.

**Translation keys** added under `matrix.*` and `filters.*` (page title, axis labels, "all domains",
"no documents in this cell", "clear filters", chip aria labels) to
[de.json/en.json seeds](../../../apps/api/scripts/seed_data/translations/) and the web
[fallback bundles](../../../apps/web/src/i18n/fallback/); the existing
[fallback.test.ts](../../../apps/web/src/i18n/fallback/fallback.test.ts) guards key parity.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/web/src/features/taxonomy/types/index.ts` | `Term`, `MatrixCell`, `MatrixResponse` |
| `apps/web/src/features/taxonomy/services/taxonomyApi.ts` | `fetchDomains`, `fetchLifeSituations`, `fetchMatrix` |
| `apps/web/src/features/taxonomy/hooks/use{Domains,LifeSituations,Matrix}Query.ts` | Query hooks |
| `apps/web/src/features/taxonomy/**/*.test.ts(x)` | Tests below |

**Edit**

| Path | Change |
| --- | --- |
| `apps/api/scripts/seed_data/translations/{de,en}.json` | New keys |
| `apps/web/src/i18n/fallback/{de,en}.json` | Same keys |

## Red tests

| Test | Asserts |
| --- | --- |
| `taxonomyApi · fetchDomains calls /api/v1/domains with locale` | URL and header |
| `taxonomyApi · fetchMatrix sends municipality_code when scoped` | Query string |
| `taxonomyApi · fetchMatrix omits the param when unscoped` | Negative |
| `useDomainsQuery · refetches when locale changes` | Key includes locale |
| `useMatrixQuery · surfaces an API error as query error` | No swallowed failure |
| `fallback bundles · de and en have identical key sets` | Existing parity test covers new keys |

## Green

1. Types and fetchers with tests using the existing `apiRequest` test seam (see
   [api.ts](../../../apps/web/src/services/api.ts)); do not mock `fetch` internals beyond it.
2. Hooks with `renderWithProviders`.
3. Translation keys in all four files.

## Refactor gate

- Three near-identical hooks: extract a small `useTaxonomyQuery(key, fetcher)` only if duplication is
  literal; otherwise leave three 5-line hooks (rule of three applies to branches, not to copies).
- Types file holds types only.

## Verification

```bash
cd apps/web
npm run test -- src/features/taxonomy src/i18n
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

## Out of scope

Any component (chapters 7–9), backend changes.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-web-client
```

```text
test(web): describe taxonomy client and hooks

feat(web): add taxonomy API client, hooks and translations
```
