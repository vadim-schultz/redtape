# Chapter: Jurisdiction hierarchy

## Goal

Model administrative levels so Germany (Bundesland, Gemeinde) fits naturally and other countries (e.g. regioni, départements) can be added without schema surgery.

## Core entities (conceptual)

- **Country** — top-level sovereign scope; ISO-3166-1 alpha-2 as stable external key where possible.
- **Region** — first subdivision below country (Land, regione, …); nullable parent only when future nested regions are needed (prefer a self-referencing `region` table or a generic `jurisdiction_node` pattern—pick one in implementation).
- **Municipality** — optional finest scope (Gemeinde, Stadt); references parent region and country for integrity and query convenience.

## Fields (minimum)

- Stable **codes** where official registers exist (e.g. AGS for German municipalities); human-readable **name** and optional **name_i18n** (JSONB or satellite table).
- **Effective dating** (`valid_from` / `valid_to`) if boundaries or mergers matter for historical accuracy; MVP may omit if only “current” data is loaded.

## Inheritance rule (read path)

Resolution precedence for a rule attached at different levels:

1. Municipality (if present and has an explicit rule row)
2. Region (Bundesland)
3. Country

Document this order in code and tests; do not rely on implicit sort without a defined policy.

## Implementation checklist

- [ ] Alembic migration: `countries`, `regions`, `municipalities` (or unified `jurisdictions` with `type` enum—decide and document tradeoff: fewer joins vs clearer semantics).
- [ ] Unique constraints on `(country_id, region_code)` and `(region_id, municipality_code)` as applicable.
- [ ] Seed script: Germany + 16 Länder + optional sample municipalities for dev.

## Open decisions

- **Unified `jurisdictions` table vs split tables:** unified simplifies “attach rule to any level” with one FK; split tables are more explicit for German forms. Recommendation: **unified `jurisdiction` with `kind` enum** and self-FK `parent_id` for simpler graph APIs.

## Related chapters

- [02-documents-and-requirements.md](02-documents-and-requirements.md)
- [03-graph-resolution-and-views.md](03-graph-resolution-and-views.md)
