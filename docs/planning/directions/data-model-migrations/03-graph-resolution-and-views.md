# Chapter: Graph resolution, queries, and views

## Goal

Define how **canonical requirements** are stored, **resolved** against jurisdiction hierarchy (see [01-jurisdiction-hierarchy.md](01-jurisdiction-hierarchy.md)), and **queried** for list/detail and tree expansion without premature optimization.

## Storage model (MVP)

- **Adjacency list** in relational tables: one row per directed edge (`parent_document` → `required_document`) with scope and provenance as in [02-documents-and-requirements.md](02-documents-and-requirements.md).
- No closure table or materialized path in v1 unless profiling shows unacceptable depth or fan-out for “full tree” endpoints.

## Read-time resolution (fallback)

When fetching **effective** requirements for document `D` at jurisdiction context `J` (e.g. user-selected municipality):

1. Collect candidate edges for `D` scoped at **municipality**, **region**, and **country** levels that apply to `J` (same country; region/municipality match `J` or ancestor scopes as modeled).
2. For each unique `(required_document_id)` target, keep the **most specific** winning row using explicit precedence: **municipality → region → country** (same order as [01-jurisdiction-hierarchy.md](01-jurisdiction-hierarchy.md)).
3. Tie-breakers (same level, overlapping validity windows): prefer **newer `valid_from`**, then **canonical** source over `import` if product policy requires—document the rule in API and tests.

Implement resolution in a **single service layer** (SQL view, repository method, or CTE) so web, mobile, and workers share behavior.

## Query patterns

| Use case | Pattern |
|----------|---------|
| Direct dependencies for one document | Filter edges by parent + resolved scope; paginate if large. |
| Reverse dependencies (“who requires this?”) | Index on `required_document_id`. |
| Full tree (BFS/DFS) | Iterative queries or batched `WHERE parent_document_id IN (...)` with cycle detection (visited set in application or `WITH RECURSIVE` with depth cap). |
| Search documents in scope | Filter documents by jurisdiction FKs + text search on localized title. |

**Cycle policy:** treat cycles as data errors for MVP: detect in admin/import; API returns partial tree with `cycle_detected` flag or 409 depending on product choice—pick one and document in [../backend-api/README.md](../backend-api/README.md).

## Caching and performance

- **MVP:** rely on Postgres indexes `(parent_document_id, jurisdiction…)`, `(required_document_id)`, and btree on slug lookups; optional short **HTTP cache** on public read endpoints.
- **Later:** materialized view or nightly rollup for hot documents; **closure table** only if recursive CTE cost dominates SLOs.

## API and client alignment

- Resolution rules must match **backend-api** graph endpoints and any **shared contracts** package; version changes to precedence require migration notes in [../devops-ci-cd/README.md](../devops-ci-cd/README.md).

## Implementation checklist

- [ ] Indexes supporting parent/required lookups and jurisdiction filters.
- [ ] Shared resolution module + unit tests for precedence matrix (municipality overrides region, etc.).
- [ ] Tree endpoint: depth limit, max nodes, cycle handling documented.
- [ ] Optional: explain-query review for worst-case trees before adding closure table.

## Related chapters

- [01-jurisdiction-hierarchy.md](01-jurisdiction-hierarchy.md)
- [02-documents-and-requirements.md](02-documents-and-requirements.md)
- Social promotion of edges: [../social-moderation/README.md](../social-moderation/README.md)
