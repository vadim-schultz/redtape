# Document matrix — gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

---

## Settled decisions

### D1 — Two independent many-to-many axes

Documents link to any number of domains and any number of life situations through two join tables.
Rejected: a single primary domain per document (too rigid — a birth certificate belongs to several
areas), and explicit per-cell rows (curation cost with no gain; cells are derivable).

### D2 — Cells are computed

A matrix cell is the intersection of `document_domain` and `document_life_situation`. Nothing stores
cells, so there is no third table to keep consistent.

### D3 — Flat, curated life situations

Eighteen seeded Germany situations, no parent/child structure. Hierarchy (Family / Work / Housing
groups) is deferred until the flat list proves too long in the UI.

### D4 — Vehicle kinds are documents, not domains

Car, motorbike and boat are represented by distinct documents inside the single `fahrzeuge-mobilitaet`
domain. Revisit only if users need to filter by vehicle kind independent of the document title.

### D5 — Postgres, no graph database

The document graph is small (thousands of nodes, depth 3–6). Recursive CTEs cover traversal; the
matrix itself is plain joins. A graph DB would add a second store to sync and secure on a free-tier
stack. Keep resolution behind one module so the engine stays swappable.

### D6 — Global taxonomy

Domains and situations are not jurisdiction-scoped. Per-jurisdiction variation is expressed by which
documents exist and how they are tagged. Other countries reuse the same taxonomy or add rows.

### D7 — Additive API only

New query params and response fields are optional/additive. No existing client breaks; the documents
list without filters returns exactly what it returns today.

### D8 — Language-neutral codes are the public identifiers (revises the original D8)

The first version of this suite used German-derived slugs (`umzug`, `geburt-kind`). That ties one
country's vocabulary into URLs and breaks the moment the product serves France or Italy. Replaced by
`code`: English-derived, ASCII kebab-case, stable forever, never translated — the same role as
`ui_translation` keys and `Jurisdiction.code`. Query params and API payloads carry codes; displayed
names come only from `name_i18n` in the request locale. Not UUIDs: codes keep links readable and
survive reseeding.

Rejected alternatives:

| Option | Why not |
| --- | --- |
| Localized slugs per locale (`umzug` / `demenagement`) | Shared links change with the reader's language, per-locale uniqueness and redirects, translators own URLs |
| German codes as canonical | Country vocabulary baked into identifiers |
| UUIDs in URLs | Unreadable, differ between environments |

Route paths (`/documents`, `/matrix`) stay English constants; localized path segments are a non-goal
until there is an SEO reason (see seams).

### D9 — Rows and columns are selectable, not just cells

The matrix supports three selections: a cell (domain and situation), a whole situation row (all
documents for that life situation), and a whole domain column (all documents for that domain), plus the
grand total. They map onto the existing documents filter with one or both params, so no extra
endpoint is needed.

### D10 — Axis totals are distinct-document counts

The matrix API returns `situations[].count` and `domains[].count` computed as `COUNT(DISTINCT document)`
per term. Summing cells would double-count documents that sit in several columns. Clients display the
totals and never derive them.

### D11 — The grid shows only terms that apply in scope

Rows and columns come from the matrix response, not from the full taxonomy lists. Terms with no
documents in the selected jurisdiction are hidden, which keeps the grid honest for other countries
without per-country configuration.

---

## Open seams (not blocking any chapter)

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Mobile vault taxonomy | Chapter 10 adds a pointer in the mobile README; no Flutter work | Mobile vault chapter starts |
| Situation as graph entry point / checklist | Matrix links to filtered lists only | Graph-resolution API ships |
| Curation and community tagging | Tags are seeded by script only | Social-moderation proposals cover metadata edits |
| Situation hierarchy | Flat list | UI grid becomes unreadable at ~25 situations |
| Matrix at scale | One aggregate query per request | Cell query exceeds budget on real data; then add a materialized view |
| Taxonomy outside Germany | Same tables and codes, German seed only; `fr`/`it` names and country-only terms added on onboarding | Second country onboarded |
| Localized URL paths | Not planned; codes and route paths are English | An SEO requirement for a market; then add `slug_i18n` with a redirect to the canonical code |
| Tags on list cards | Detail header only; `DocumentCard` shows no badges | Users need tags while browsing; needs additive `domains`/`life_situations` on `DocumentSummary` (eager-load per page) and a card layout without nested anchors, since the whole card is already a link to detail |
| Highlighting the selection in the list | The active chip shows the selection | Users lose track of which matrix row they came from |
