# OpenPLZ import (Germany locations → Postgres)

This project imports administrative geography from the public [OpenPLZ API](https://www.openplzapi.org/en/germany/) into our Postgres schema.

## What gets stored

The import script populates:

- `jurisdiction`
  - `kind=COUNTRY` (root row for `DE`)
  - `kind=REGION` for OpenPLZ `FederalStates` and for OpenPLZ `Districts` (as a unified hierarchy level)
  - `kind=MUNICIPALITY` for OpenPLZ `Municipalities`
- `locality`
  - postal-code localities under a `jurisdiction (MUNICIPALITY)` row

Only **German names** are written for both `de` and `en` during MVP (so the app can display something consistently before we add proper EN translations later).

## Source & paging

OpenPLZ endpoints use:

- `page` and `pageSize` query parameters (max `pageSize=50`)
- paging response headers (not required for this importer; we iterate pages until results are empty)

See: OpenPLZ paging docs: [Paging](https://www.openplzapi.org/en/paging/).

## Script entrypoint

`apps/api/scripts/import_openplz_locations.py`

### Run locally (manual import)

From the `apps/api` folder:

```bash
python scripts/import_openplz_locations.py --language de
```

Useful flags:

- `--dry-run` (parse only; no DB commit)
- `--commit-every N` (DB commit batch size, default `1000`)

### Database migration pre-step

Before importing, run Alembic migrations:

```bash
alembic upgrade head
```

## Idempotency & cache refresh

The importer uses deterministic UUIDs so re-running does not create duplicates.

It also updates `last_updated` for rows it touches, so Supabase connection/security policies and any cache-busting logic based on timestamps can keep working.

## Scheduled nightly updates

Runs on GitHub Actions, not GitLab. See: [`docs/operations/scheduled-jobs.md`](scheduled-jobs.md).

