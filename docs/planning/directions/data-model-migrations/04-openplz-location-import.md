# OpenPLZ location import (shipped, previously undocumented)

This chapter documents a subsystem that was built and shipped alongside Waves 1–2 but had no entry anywhere in the planning docs until now. It supplies the real German administrative-geography data (states, districts, municipalities, postal-code localities) that [01-jurisdiction-hierarchy.md](01-jurisdiction-hierarchy.md) models — the MVP roadmap's seed script (B9) only inserts one hand-picked Land/city; this import populates the rest of Germany.

## What it stores

Source: the public [OpenPLZ API](https://www.openplzapi.org/en/germany/) (paginated, `page`/`pageSize` up to 50).

The importer populates:

- `jurisdiction`
  - `kind=COUNTRY` — one root row for `DE`
  - `kind=REGION` — OpenPLZ `FederalStates` **and** `Districts`, both folded into the unified `jurisdiction` hierarchy (matching the "unified table with `levels[]`" decision in [01-jurisdiction-hierarchy.md](01-jurisdiction-hierarchy.md))
  - `kind=MUNICIPALITY` — OpenPLZ `Municipalities`
- `locality` — postal-code-level rows nested under a `MUNICIPALITY` jurisdiction (added by migration `20260520_openplz_locations`, alongside `type`/`postal_code`/`multiple_postal_codes`/`last_updated` columns on `jurisdiction`)

Only German names are written for both `de` and `en` during MVP — English administrative names aren't sourced yet, so the `de` string is duplicated into `name_i18n.en` so the app has something consistent to render before real EN translations are added.

Rows use **deterministic (UUIDv5) IDs** so re-running the import is idempotent and never duplicates data on its own.

## API surface

`apps/api/app/features/locations/` exposes the hierarchy read-only, mounted under `/api/v1`:

- `GET /api/v1/countries`
- `GET /api/v1/states?country=`
- `GET /api/v1/districts?state=`
- `GET /api/v1/cities?district=`
- `GET /api/v1/localities?city=`

`apps/web`'s location-picker filter (state → district → city, under `features/locations/`) is built on top of these — this is why Wave 2's shipped web app is larger than the roadmap's W1–W7 list describes.

## Jobs and scripts

- **Import:** [`apps/api/scripts/import_openplz_locations.py`](../../../../apps/api/scripts/import_openplz_locations.py) — `python scripts/import_openplz_locations.py --language de` (flags: `--dry-run`, `--commit-every N`). Run after `alembic upgrade head`. Scheduled nightly via GitHub Actions — see [docs/operations/scheduled-jobs.md](../../../operations/scheduled-jobs.md) (not GitLab, despite older ops docs).
- **Cleanup:** [`apps/api/scripts/cleanup_openplz_data.py`](../../../../apps/api/scripts/cleanup_openplz_data.py) — recomputes the expected deterministic UUIDs for OpenPLZ-derived rows and reconciles mismatches (`--dry-run` supported).

## Incident: duplicate jurisdiction rows

Migration `20260610_fix_dup_juris` is a data-repair migration, not a schema addition. Before the `(geographic_parent_id, code)` uniqueness was enforced, repeated/overlapping imports produced duplicate `jurisdiction` rows for the same administrative unit. The migration:

1. Deduplicates existing `jurisdiction` rows violating that uniqueness (keeps the most-recently-updated row per group).
2. Remaps foreign keys on `locality`, `document`, and `document_requirement` that pointed at the rows being removed, including descendants of colliding rows (recursive re-parenting).
3. Adds the `uq_jurisdiction_parent_code` unique constraint (checked idempotently via `pg_constraint` before creating it).

The nightly import workflow now asserts this constraint exists as a guard step before importing, specifically so this class of duplication can't silently recur. `scripts/cleanup_openplz_data.py` is the standalone/manual counterpart if drift is ever suspected again outside of a migration run.

## Troubleshooting

See [docs/operations/troubleshooting-openplz.md](../../../operations/troubleshooting-openplz.md) for DNS/rate-limit/schema-mismatch/translation issues.
