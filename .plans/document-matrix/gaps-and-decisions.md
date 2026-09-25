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

### D8 — Slugs are the public identifiers

URLs and query params use ASCII slugs, never UUIDs, so links are readable and survive reseeding.

---

## Open seams (not blocking any chapter)

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Mobile vault taxonomy | Chapter 10 adds a pointer in the mobile README; no Flutter work | Mobile vault chapter starts |
| Situation as graph entry point / checklist | Matrix links to filtered lists only | Graph-resolution API ships |
| Curation and community tagging | Tags are seeded by script only | Social-moderation proposals cover metadata edits |
| Situation hierarchy | Flat list | UI grid becomes unreadable at ~25 situations |
| Matrix at scale | One aggregate query per request | Cell query exceeds budget on real data; then add a materialized view |
| Taxonomy outside Germany | Same tables, German seed only | Second country onboarded |
