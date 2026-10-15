# Scheduled jobs (platform maintenance)

This project has no GitLab CI — all scheduling runs on **GitHub Actions**. OpenPLZ import and discovery online share one workflow: [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml).

## Workflow

`Platform maintenance` (`.github/workflows/platform-maintenance.yml`):

- **Triggers:** `schedule` — daily cron `0 2 * * *` (02:00 UTC), and `workflow_dispatch` with optional `job` input (`openplz`, `discovery`, or `skip`).
- **Router:** [`scripts/maintenance_job_router.py`](../../scripts/maintenance_job_router.py) computes `days_since_anchor % 6` with anchor **`2026-01-01` UTC** (`MAINTENANCE_ANCHOR_DATE` in the workflow).  
  | `days % 6` | Job |
  | --- | --- |
  | `0` | OpenPLZ import |
  | `3` | Discovery online (placeholder until later chapters) |
  | `1`, `2`, `4`, `5` | No-op (`skip`, success) |
- **OpenPLZ job steps:** checkout → Python 3.12 → `pip install -e .` in `apps/api` → `alembic upgrade head` → verify `uq_jurisdiction_kind_code` on `jurisdiction` → `python scripts/import_openplz_locations.py --language de`.
Manual override ignores the calendar when `job` is set on `workflow_dispatch`.

## Repository secrets (GitHub Actions)

Configure these under **Settings → Secrets and variables → Actions** for the repo.

| Secret | OpenPLZ job (`days % 6 == 0`) | Discovery job (`days % 6 == 3`) | Notes |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | **no** | Supabase pooler URL; migrations + OpenPLZ import only |
| `DISCOVERY_API_URL` | no | yes | Render **host root**, e.g. `https://redtape-api.onrender.com` — ingest client adds `/api/v1/discovery/machine/...` |
| `DISCOVERY_API_KEY` | no | yes | `rt_…` from `python -m scripts.issue_api_key --name discovery-scheduled-gha` (`apps/api`) |
| `FEDERAL_JURISDICTION_ID` | no | yes | Germany seed UUID `11111111-1111-1111-1111-111111111101` |

Optional workflow environment variables (defaults in [`discovery_ingest/config.py`](../../apps/discovery-ingest/discovery_ingest/config.py)):

| Variable | Purpose |
| --- | --- |
| `GOVDATA_CKAN_BASE_URL` | GovData CKAN API base |
| `PVOG_API_BASE_URL` | PVOG Suchdienst API base |
| `FIM_PORTAL_BASE_URL` | FIM portal base for enrich |

Discovery ingest never uses `DATABASE_URL` in GHA (machine API boundary). Laptop runbook:
[`discovery-layer.md`](discovery-layer.md).

## Manually triggering a run

GitHub → **Actions** → **Platform maintenance** → **Run workflow**, or via the CLI:

```bash
# Calendar router for today (UTC)
gh workflow run platform-maintenance.yml

# Force OpenPLZ or discovery for debugging
gh workflow run platform-maintenance.yml -f job=openplz
gh workflow run platform-maintenance.yml -f job=discovery
gh workflow run platform-maintenance.yml -f job=skip
```

The legacy **OpenPLZ Import** workflow ([`openplz-import.yml`](../../.github/workflows/openplz-import.yml)) remains for manual `workflow_dispatch` only; its Mon+Thu schedule was retired in favor of the unified maintenance router.

## Related

- Import script details: [openplz-import.md](openplz-import.md)
- Import script: [`apps/api/scripts/import_openplz_locations.py`](../../apps/api/scripts/import_openplz_locations.py)
- Render keep-alive ping (separate): [`.github/workflows/keep-alive.yml`](../../.github/workflows/keep-alive.yml)
