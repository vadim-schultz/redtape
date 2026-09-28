# Scheduled jobs (OpenPLZ import)

This project has no GitLab CI — all scheduling runs on **GitHub Actions**. The OpenPLZ import is implemented in [`.github/workflows/openplz-import.yml`](../../.github/workflows/openplz-import.yml).

## Workflow

`OpenPLZ Import` (`.github/workflows/openplz-import.yml`):

- **Triggers:** `workflow_dispatch` (manual, on demand) and `schedule` — Monday + Thursday cron `0 2 * * 1,4` (2:00 UTC). This cadence also incidentally keeps the Supabase free-tier project from going idle (auto-pauses after ~7 days of inactivity); twice weekly leaves a full run's margin if any single run fails, unlike a strict weekly cadence.
- **Steps:** checkout → set up Python 3.12 → `pip install -e .` in `apps/api` → `alembic upgrade head` → verify the `uq_jurisdiction_kind_code` unique index exists on `jurisdiction` (fails loudly if a migration was skipped) → run `python scripts/import_openplz_locations.py --language de`.
- **Secrets:** `DATABASE_URL` (repo secret) is the only credential used; it points at the same Postgres the API uses.

## Manually triggering a run

GitHub → **Actions** → **OpenPLZ Import** → **Run workflow** (uses `workflow_dispatch`), or via the CLI:

```bash
gh workflow run openplz-import.yml
```

## Related

- Import script details: [openplz-import.md](openplz-import.md)
- Import script itself: [`apps/api/scripts/import_openplz_locations.py`](../../apps/api/scripts/import_openplz_locations.py)
