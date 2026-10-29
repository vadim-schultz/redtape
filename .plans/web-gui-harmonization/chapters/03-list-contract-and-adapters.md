---
name: "Chapter 3 — Stable list contract and adapters"
overview: "Standardise server-side pagination, sorting, search, filters, validation, and typed frontend adapters without changing unrelated discovery behavior."
todos:
  - id: api-contract
    content: "Extend shared list-query models and validation with allowlisted sort and filter semantics."
    status: pending
  - id: adapters
    content: "Map typed DataTable query state through web services and URL state adapters."
    status: pending
  - id: tests
    content: "Add API and web paired tests for valid and invalid list queries."
    status: pending
isProject: false
---

# Chapter 3 — Stable list contract and adapters

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/web-gui-harmonization-list-contract` · **Status:** planned  
**Depends on:** [02-data-table-kernel.md](02-data-table-kernel.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-web-gui-harmonization` · **Release branch:** `main`

## Goal

The API and web clients share one typed list contract. Existing `offset`/`limit` behavior remains
compatible, while resources can opt into validated `sort_by`, `sort_order`, `q`, and typed filters.
Responses expose the full filtered `total`, and frontend adapters serialize URL-backed query state
without making the DataTable aware of API field names.

## Design decisions

- Keep `offset`, `limit`, and `{items,total,offset,limit}` as the compatibility core.
- Add canonical `sort_by`, `sort_order`, `q`, and bracketed `filter[field]` query names only through
  typed resource models and allowlists.
- Unknown fields, invalid enum/operator/value combinations, and out-of-range limits receive the
  existing validation error shape. No arbitrary SQL/order expression reaches a repository.
- Apply a deterministic secondary ordering per resource.
- Keep legacy resource-specific query names as aliases only when existing callers require them; the
  canonical web adapter emits one shape.
- URL parsing is pure and rejects invalid values to defaults. A filter, search, or sort change sets
  `offset=0`.

## Files

**Edit**

- `apps/api/app/shared/paging.py` and the shared query/validation module selected by the API layout
- discovery list controllers, query models, and resource-specific sort/filter allowlists
- API tests beside the changed controllers/models
- `apps/web/src/app/queryKeys.ts` only if query identity needs the canonical state
- discovery service types, adapters, and URL-state hooks
- web tests for serialization and query reset semantics

**Do not edit**

- auth/admin allowlists
- ingestion workers, crawler behavior, or unrelated persistence models
- DataTable presentation internals from chapter 2

## Red tests

| Test | Asserts |
| --- | --- |
| `candidate list accepts an allowlisted sort and filter query` | A valid typed request returns the expected page envelope and full filtered total. |
| `list query applies deterministic secondary ordering` | Equal primary values produce stable page order across repeated requests. |
| `list query rejects an unknown sort field` | Negative: the API returns explicit validation failure and performs no repository query. |
| `list query rejects an invalid filter value` | Negative: malformed enum/numeric/filter input is rejected with the stable validation shape. |
| `query state serializes canonical list parameters` | Valid web state maps to canonical URL/API parameters. |
| `query state resets offset when sort or filter changes` | Negative: stale page offsets are not retained after a query-shaping change. |

Write and run the API and web pairs before implementation.

## Green

1. Add pure API query models and validation tests.
2. Extend the shared pagination envelope while keeping existing callers green.
3. Add resource allowlists and deterministic ordering.
4. Add web URL parsing/serialization and typed service adapters.
5. Update one candidate endpoint as the reference adapter, then generalize only repeated behavior.
6. Run narrow pytest and Vitest suites after each extraction.

## Refactor gate

Audit the whole query model, controller boundary, URL parser, and adapter module. Extract repeated
validation and serialization mappings into named units; keep resource-specific differences in typed
allowlists rather than adding a growing conditional chain. Check that no boolean mode or untyped
dictionary crosses the boundary without validation. Report the outcome and rerun both narrow suites.

## Verification

```bash
pytest apps/api/tests -k "paging or list_query or discovery_admin"
cd apps/web
npm run test -- src/features/discovery-admin --run
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Out of scope

- Migrating every table consumer
- New database indexes unless query tests prove an existing query is unusable
- Public UI redesign
- Arbitrary full-text search infrastructure

## Git workflow

```bash
git checkout feat/plans-web-gui-harmonization && git pull
git checkout -b feat/web-gui-harmonization-list-contract
```

Suggested commits:

```text
test(api): define validated list query contract
feat(api): expose canonical discovery list parameters
feat(web): serialize typed list state for admin queries
```

Open the chapter PR into `feat/plans-web-gui-harmonization`.

