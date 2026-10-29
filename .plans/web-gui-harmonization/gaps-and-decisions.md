# Web GUI harmonization — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled decisions

### D1 — Reuse interaction structure, keep the RedTape product skin

The reference UI is design input, not a dependency or a brand source. Copy useful component
boundaries, elevation language, table ergonomics, and pagination behavior into `apps/web`. Keep the
RedTape red palette, current typography, product terminology, routes, and i18n.

### D2 — One DataTable for operational data

The shared DataTable is the only table presentation primitive for discovery admin list views. Feature
column builders supply labels, formatters, links, and allowed sort/filter keys. Direct feature-level
`Table.Root` implementations are removed or retained only for a genuinely different semantic surface
that is documented in this file.

### D3 — Cards remain for content-oriented previews

Document cards can remain on public browse pages when title, description, and destination form one
preview unit. They do not establish a second admin data language. Coverage, queues, candidates,
catalogue rows, mentions, budgets, and other comparable records use DataTable.

### D4 — Elevation is tokenized and restrained

Every raised shell combines the existing semantic surface role with a subtle border and one named
shadow. Static shells do not lift on hover. Linked cards may use the existing hover lift. No raw
hex, arbitrary shadow string, or nested decorative card is added to compensate for missing spacing.

### D5 — URL state is canonical for admin lists

Admin search, filters, sort, page offset, and page size serialize to the URL. A single typed state
adapter owns parsing, validation, defaults, and reset-to-first-page behavior. Local component state
is allowed only for transient popover input before Apply.

### D6 — Page size and response metadata

The default page size is the shared API default (`20`) unless a resource has a documented reason to
use a smaller or larger value. The API caps the page size at its existing maximum. Every paginated
response reports `{items,total,offset,limit}`, where `total` is calculated after filters.

### D7 — Sort and filter capabilities are explicit

Columns declare their server key and capabilities. Display-only columns have no sort/filter control.
The API maps public keys to allowlisted expressions and rejects unknown keys. Default sorting and
stable secondary ordering are defined per resource.

### D8 — Filter operators are deliberately small

The first contract supports the operators needed by current admin data: equality, contains/search,
multi-value membership, and numeric/date comparisons where a resource requires them. A resource does
not advertise an operator merely because the generic table can render it.

### D9 — Pagination uses Chakra compound components

The shared pagination control uses Chakra's `Pagination.Root` family and preserves keyboard and
screen-reader semantics. It is hidden when there is one page, resets when query state changes, and
supports narrow layouts without hiding the current range.

### D10 — Chevron ownership stays with the menu suite

The existing [frontend-ui-menu chapter](../frontend-ui-menu/chapters/01-remove-list-chevron.md) owns
the non-functional document-count chevron removal. This suite verifies the final integration and
does not create a second implementation or competing test.

### D11 — Interaction coverage per surface (chapter 6)

| Surface | Server operations | Why |
| --- | --- | --- |
| Discovery documents | `sort_by` (title, mentions, created_at), `q`, `filter[status\|role\|source\|min_mentions]`, paging | Chapter 3 contract |
| Discovery tasks | `sort_by` (target, kind, status, source, priority, attempts), `q` over the target URL, `filter[status\|source\|kind]`, paging | Operators triage the queue by these fields; timestamps (retry, lease) are nullable and not sorted |
| Catalogue index | `sort_by` (external_id, source, stage), `q` over the external id, `filter[source]`, paging | The fixed page of 50 silently cut larger catalogues |
| Mentions, edges, stored pages | none | Each is one candidate's (or catalogue row's) complete set from an unpaged endpoint in a fixed order; there is nothing to push to a server, and a client-side sort would contradict D7 |
| Coverage metrics | none | Static summaries, chapter 5 |
| Public documents, suggestions | none yet | See below |

URL state is canonical for all three paged admin lists. A filter applied from a column header or the
documents toolbar is visible (summary chips or the select value), removable, and resettable.
A failed refetch keeps the previous rows with a retryable alert; a failure with no rows (first load,
or a changed query whose placeholder data TanStack Query drops) shows the error in the table shell
with the header controls still reachable.

**Public list audit.** `GET /documents` and `GET /suggestions` already return
`{items,total,offset,limit}` and filter by taxonomy codes, municipality, status, kind and
jurisdiction, but the web clients never send `offset` or `limit` and never read `total`, so each
list shows at most the first 20 rows. There is no sort or search requirement in either API, and the
cards are content previews (D3). Nothing is changed in this chapter: adding paging to a public
browse page is a product decision (open seam above) rather than a table-interaction defect, and the
exposure only appears once a filter matches more than 20 records. The truncation is recorded here so
the decision is made deliberately.

### D12 — Release hardening (chapter 8)

- **Accessibility lives in the shared kernel.** The scroll container is a named, focusable group
  (`common.table.scroll_region`), loading rows are a named `status`, the filter popover is a named
  dialog on the `surface.overlay` and `dropdown` shadow tokens, and a column may declare
  `align: "end"` (applied to the coverage value columns, task priority and attempts, and the
  document mention count).
- **Edge lists and stored-page tables** now sit in `SectionCard` (`DocumentEdgesPanel`,
  `ArtifactsPanel`). Their inner captions stay as the table names.
- **Architecture rule.** Only `components/data-display/DataTable` may import Chakra's `Table` or
  render a raw `<table>`.
- **Manual browser smoke was not performed** by any chapter implementer (no browser). The
  checklist is [docs/operations/admin-tables.md](../../docs/operations/admin-tables.md#release-smoke-checks)
  and stays open for a human before or after the release PR.
- **Recorded follow-ups, not done here:** the pipeline detail page has no route-level integration
  guard; screenshot thumbnails, tag-support chips, the pipeline timeline, and emit previews stay
  outside the table language by design; the jsdom "Could not parse CSS stylesheet" warnings (27 in
  the full run) are identical on `main` before this suite and are not caused by it; D11 (public
  list paging) remains a product decision.

## Open seams

| Seam | Current position | Forcing condition |
| --- | --- | --- |
| Generic filter wire syntax | Use the bracketed `filter[field]` shape in the architecture contract | API framework constraints or generated OpenAPI representation |
| Public document/suggestion pagination | Audited in D11: cards stay, first 20 rows only; the API already returns `total` | Product decision that public browsing needs server search or paging |
| Coverage grouping | Prefer several small semantic tables over one wide metric table | Usability smoke test shows the groups are still difficult to scan |
| Mentions sorting/filtering | Closed in D11: static, the endpoints are unpaged and fixed-order | API query cost or missing indexes |
| Page-size selector | Start with the shared default and a fixed limit | Operator feedback requires user-selectable sizes |
| API compatibility aliases | Keep existing resource-specific query names during migration | All clients have moved to the canonical query shape |
| Existing visual-theme chapters | Consume their decisions and avoid parallel token rewrites | Theme contract changes before this suite starts |

## Explicit non-goals

- Do not copy domain-specific lifecycle, matrix, or navigation chrome.
- Do not change auth, admin allowlists, crawler ingestion, or database schema for unrelated reasons.
- Do not replace every badge with a table cell when the badge is a useful semantic cell value.
- Do not add a generic abstraction with one caller merely to make the tree look uniform.
- Do not remove cards from content-oriented public browse pages without a measured scanning benefit.

