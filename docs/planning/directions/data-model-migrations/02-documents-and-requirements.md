# Chapter: Documents and requirements

## Goal

Represent bureaucratic **document types** (and optionally instances) and **directed dependencies**: “to obtain or use A, you need B” scoped to a jurisdiction.

## Document

Fields to plan in schema (names indicative):

- Surrogate primary key `id` (UUID or bigint).
- **Jurisdiction FKs** — country, optional region, optional municipality (nullable upward).
- **Slug** — stable within jurisdiction scope for URLs.
- **Titles and descriptions** — localized via `jsonb` (`{"de": "...", "en": "..."}`) or child `document_locale` rows.
- **Official URL** (optional) — primary human-facing source; also used by freshness crawler.
- **Metadata** — validity hints, category tags, `jsonb` for extensibility without migrations for every country-specific attribute.

## Requirement (edge)

Directed edge: **parent_document_id** → **required_document_id**, always in a **jurisdiction scope** at least as specific as the parent (product rule: validate in app or DB constraint).

Additional columns:

- **Source** — enum: `canonical`, `import`, `accepted_proposal`, etc.
- **Provenance** — optional FK to proposal or import batch.
- **Effective dates** — `valid_from`, `valid_to` nullable for time-bound rules.
- **Notes** — localized explanation for why the edge exists (citation text).

Uniqueness: `(parent_document_id, required_document_id, jurisdiction_scope…, valid_from)` TBD to allow superseding edges.

## Separation from social layer

- **Canonical** graph: rows approved through editorial process or voting threshold (exact promotion workflow in [../social-moderation/README.md](../social-moderation/README.md)).
- **Proposals** live in social tables; on acceptance, insert or update canonical requirement rows and link provenance.

## Next chapter

- [03-graph-resolution-and-views.md](03-graph-resolution-and-views.md)
