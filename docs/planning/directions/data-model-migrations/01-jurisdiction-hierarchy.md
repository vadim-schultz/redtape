# Chapter: Jurisdiction hierarchy

## Goal

Model administrative levels so Germany (Bundesland, Gemeinde, Kreisfreie Stadt) fits naturally and other countries (e.g. regioni, départements) can be added without schema surgery.

## Core entities (conceptual)

**Recommended implementation:** a single self-referencing **`jurisdiction`** table (see open decision below) rather than three separate tables, so every rule attaches with one FK.

- **Country** — top-level sovereign scope; ISO-3166-1 alpha-2 as stable external key where possible (`code`, `kind=COUNTRY`).
- **Region** — first subdivision below country (Land, …); `kind=REGION`, `parent_id` → country.
- **Municipality** — finest scope when present (`kind=MUNICIPALITY`, `parent_id` → region or another jurisdiction as modeled).

### `levels[]` (discussion alignment)

Some German units satisfy **more than one** administrative level at once (e.g. a **Kreisfreie Stadt** behaves as both district and municipality; **Hamburg** collapses multiple levels). Store a PostgreSQL `text[]` (or equivalent) **`levels`** on `jurisdiction`: values such as `COUNTRY`, `REGION`, `DISTRICT`, `MUNICIPALITY`. Resolution walks the **parent chain** and treats applicability by containment, not by assuming a fixed depth everywhere.

## Fields (minimum)

- Stable **`code`** where official registers exist (e.g. AGS for German municipalities); **`name_i18n` JSONB** (at least `de` and `en` for MVP) instead of a single free-text `name` column.
- **`levels`** as above (can be empty only for transitional data—prefer explicit values at seed time).
- **Effective dating** (`valid_from` / `valid_to`) if boundaries or mergers matter for historical accuracy; MVP may omit if only “current” data is loaded.

## Inheritance rule (read path)

Resolution precedence for a rule attached at different levels:

1. Municipality (if present and has an explicit rule row)
2. Region (Bundesland)
3. Country

Document this order in code and tests; do not rely on implicit sort without a defined policy.

## Implementation checklist

- [ ] Alembic migration: unified **`jurisdiction`** table (`kind`, `parent_id`, `code`, `levels` text[], `name_i18n` JSONB) — **do not** ship MVP with parallel `countries` / `regions` / `municipalities` tables unless you document why the split is needed.
- [ ] Unique constraints appropriate to `code` + `parent_id` (and country root uniqueness).
- [ ] Seed script: Germany + 16 Länder + at least one sample municipality (with realistic `levels`) for dev.

## Open decisions

- **Unified `jurisdiction` table vs split tables:** **Choose unified** for Redtape unless a strong reason appears later. It matches the discussion’s “list of levels this unit satisfies” model, keeps FK shapes stable for requirements, and pairs cleanly with [i18n-localization](../i18n-localization/README.md) (`name_i18n`).

## Related chapters

- [02-documents-and-requirements.md](02-documents-and-requirements.md)
- [03-graph-resolution-and-views.md](03-graph-resolution-and-views.md)
