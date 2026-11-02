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

The importer uses deterministic UUIDs so re-running does not create duplicates. Rows are looked up and reconciled by `(kind, code)` — the DB's real uniqueness guarantee (`uq_jurisdiction_kind_code`) — so a row that needs to move to a different parent (e.g. a corrected hierarchy or a stale/misparented row) is repointed in place instead of causing a duplicate-key failure.

The importer preloads the existing jurisdictions and localities with one query each, compares every OpenPLZ record in memory, and writes only rows that are new or differ. A repeat run over unchanged data performs no `INSERT` or `UPDATE`, so it finishes in the time it takes to fetch the pages.

`last_updated` is set when a row is inserted or changed, not on every run. Nothing at runtime reads it as "last import time" (decision D11 in the GitHub Actions budget plan); the only readers are the one-shot dedupe migrations that used it as a tie-break.

## Resetting/wiping location data

`apps/api/scripts/cleanup_openplz_data.py --wipe-all` deletes every row from `document_requirement`, `document`, `locality` and `jurisdiction` (in FK-safe order), so the next import + seed starts from a clean slate. It aborts if `suggestion` has any rows, since that table isn't OpenPLZ-derived and may hold real user-submitted content — pass `--include-suggestions` to delete those too once you've confirmed that's safe. Use `--dry-run` first to see row counts without deleting anything.

```bash
python -m scripts.cleanup_openplz_data --wipe-all --dry-run
python -m scripts.cleanup_openplz_data --wipe-all
python -m scripts.import_openplz_locations --language de
python -m scripts.seed_jurisdictions
```

## Scheduled updates

Runs on GitHub Actions, not GitLab. See: [`docs/operations/scheduled-jobs.md`](scheduled-jobs.md).

