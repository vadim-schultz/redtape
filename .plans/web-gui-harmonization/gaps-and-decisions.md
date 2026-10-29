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

## Open seams

| Seam | Current position | Forcing condition |
| --- | --- | --- |
| Generic filter wire syntax | Use the bracketed `filter[field]` shape in the architecture contract | API framework constraints or generated OpenAPI representation |
| Public document/suggestion pagination | Audit first; keep cards unless scale and API metadata justify a table/list change | Product decision that public browsing needs server search or paging |
| Coverage grouping | Prefer several small semantic tables over one wide metric table | Usability smoke test shows the groups are still difficult to scan |
| Mentions sorting/filtering | Expose only fields with deterministic API semantics | API query cost or missing indexes |
| Page-size selector | Start with the shared default and a fixed limit | Operator feedback requires user-selectable sizes |
| API compatibility aliases | Keep existing resource-specific query names during migration | All clients have moved to the canonical query shape |
| Existing visual-theme chapters | Consume their decisions and avoid parallel token rewrites | Theme contract changes before this suite starts |

## Explicit non-goals

- Do not copy domain-specific lifecycle, matrix, or navigation chrome.
- Do not change auth, admin allowlists, crawler ingestion, or database schema for unrelated reasons.
- Do not replace every badge with a table cell when the badge is a useful semantic cell value.
- Do not add a generic abstraction with one caller merely to make the tree look uniform.
- Do not remove cards from content-oriented public browse pages without a measured scanning benefit.

