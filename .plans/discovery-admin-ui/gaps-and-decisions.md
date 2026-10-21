---
name: Discovery admin UI — Gaps and decisions
overview: "Settled route, authorization, component-reuse, icon, and menu behavior for the discovery admin UI remediation."
isProject: false
---

# Discovery admin UI — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | `/admin/discovery/coverage` becomes a first-class web route backed by the existing coverage hook and `CoverageChips`; it is not only an API endpoint or an undocumented alias. |
| D2 | `/admin/discovery` continues redirecting to `catalogue`; `pipeline/:id` remains row-driven; emit preview remains inside the pipeline page. |
| D3 | Discovery menu links are admin-only after the existing `/admin/discovery/tasks?limit=1` probe succeeds. The server guard remains the security boundary and no email list enters the bundle. |
| D4 | The Documents row keeps its existing `KeyValueRow` and Chakra layout. Browse and Suggest become icon-only links using existing `react-icons/fa` imports where available: `FaSearch` and `FaArrowUp`. |
| D5 | Home is a full-width `Button asChild`/router link at the top of `AppMenuPanel`, above the key-value rows, so it spans the complete panel rather than adding a label/value row. It links to `/`, preserving the existing root redirect. |
| D6 | Discovery links use readable text labels under the Documents group. The icon-only requirement applies to Browse Documents and Suggest, not to the admin links whose labels disambiguate Catalogue, Coverage, and Tasks. |
| D7 | Reuse existing `AppMenuPanel`, `DocumentsMenuRow`, `KeyValueRow`, `CoverageChips`, `QueryError`, `EmptyStateCard`, React Query keys, and API service functions before introducing new components. |
| D8 | A visible loading state replaces `null` for guard and discovery lazy-route waits. `401`, `403`, `503`, network failure, empty data, and unknown route each have distinct user-observable outcomes. |

## Open seams

- Whether the coverage page should later grow charts or filtering; the first implementation stays at the
  existing DTO and chip summary.
- Whether discovery links should become a separate top-level menu group after the admin surface grows
  beyond Catalogue, Coverage, and Tasks.
- Whether a production cold-start notice should be shared with the admin loading state; the initial
  remediation reuses existing feedback components and avoids changing global shell behavior.

## Out of scope

- Backend route, schema, migration, or ingest-worker changes.
- Supabase provider changes or client-side email allowlist logic.
- A new icon package. If an existing Font Awesome icon does not meet the final visual review, select
  another icon from the already-installed `react-icons` package rather than adding a dependency.
- A standalone pipeline menu link without a catalogue service id.
