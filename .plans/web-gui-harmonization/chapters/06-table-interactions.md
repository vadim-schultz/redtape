---
name: "Chapter 6 — Filter, search, sort, and pagination completion"
overview: "Apply the list interaction contract consistently to every meaningful discovery admin column and audit public list behavior."
todos:
  - id: admin-interactions
    content: "Wire column sort/filter/search controls and URL state for all migrated admin tables."
    status: pending
  - id: public-audit
    content: "Audit public document and suggestion lists and implement only justified server-backed interactions."
    status: pending
  - id: tests
    content: "Add state-transition and refetch regression tests."
    status: pending
isProject: false
---

# Chapter 6 — Filter, search, sort, and pagination completion

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/web-gui-harmonization-table-interactions` · **Status:** planned  
**Depends on:** [03-list-contract-and-adapters.md](03-list-contract-and-adapters.md), [04-discovery-admin-tables.md](04-discovery-admin-tables.md), [05-coverage-metrics-tables.md](05-coverage-metrics-tables.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-web-gui-harmonization` · **Release branch:** `main`

## Goal

Every discovery admin table offers the interactions that are meaningful for its data: server-backed
sort, column filters, global search, result counts, URL persistence, page reset, and Chakra
pagination. Public documents and suggestions receive an evidence-based audit and only gain table or
pagination behavior when their API and product use case justify it.

## Design decisions

- The column declaration is the source of truth for control availability and API key mapping.
- Search is global when users search across a resource; column filters are used for bounded fields.
- Applied filters are visible, removable, and resettable. Transient filter-popover input is local
  until Apply.
- URL state is canonical for admin views and feeds query keys. Invalid URL values fall back to safe
  defaults and do not crash the page.
- Filter, sort, search, and page changes reset `offset=0`; changing only page preserves all other
  query state.
- A failed refetch keeps the previous rows visible and exposes a retryable error. A first-load
  failure has no stale table to show.
- “Every column” means every column with a meaningful, allowlisted server operation. IDs, rendered
  action cells, and long free-form excerpts are not forced into misleading filters.

## Files

**Edit**

- discovery admin filter components and state hooks
- DataTable header/filter/pagination adapters
- discovery service query mappings and API resource models as required by the contract
- public documents/suggestions query hooks only where the audit selects them
- tests beside all changed hooks/components/services

**Add**

- shared URL list-state parser/serializer if chapter 3 did not place it in a reusable location
- active-filter summary/reset component if repeated across admin views

**Do not edit**

- unrelated public routes
- authorization logic
- metric-table presentation from chapter 5 except to connect shared interactions

## Red tests

| Test | Asserts |
| --- | --- |
| `changing a filter resets the admin table to the first page` | The next query has `offset=0` and keeps unrelated state. |
| `changing sort resets the admin table and serializes direction` | Sort field/order reach the typed adapter and reset paging. |
| `clearing filters restores the default result set` | Clear removes URL/API filter parameters and returns page one. |
| `invalid URL list state falls back to safe defaults` | Negative: malformed page, sort, or filter values do not reach the API. |
| `refetch failure preserves previous rows with visible feedback` | Negative: a failed background request does not blank the current table and remains retryable. |
| `single-page result hides pagination controls` | The user does not see non-functional navigation. |

Run each happy/negative pair before implementation.

## Green

1. Define pure state transition and URL serialization tests.
2. Wire one admin table end to end.
3. Extract repeated active-filter/reset behavior into a shared unit only after a second caller exists.
4. Apply the interaction contract to the remaining admin tables and supported API fields.
5. Run the public-list audit; implement only the chosen, justified scope.

## Refactor gate

Audit the complete list-state hook, URL parser, filter toolbar, and table-header interaction paths.
Flatten nested state transitions, extract repeated query-reset logic, and ensure a single state
object—not a tuple of fields—is passed between URL, hook, service, and table boundaries. Report the
outcome and rerun the narrow suite after each extraction.

## Verification

```bash
pytest apps/api/tests -k "list_query or discovery_admin"
cd apps/web
npm run test -- src/features/discovery-admin src/components/data-display
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Out of scope

- Advanced saved searches
- Full-text indexing
- Bulk row actions
- New public product navigation

## Git workflow

```bash
git checkout feat/plans-web-gui-harmonization && git pull
git checkout -b feat/web-gui-harmonization-table-interactions
```

Suggested commits:

```text
test(web): define list interaction reset semantics
feat(web): complete admin table filtering and pagination
```

Open the chapter PR into `feat/plans-web-gui-harmonization`.

