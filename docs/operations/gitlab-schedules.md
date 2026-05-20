# GitLab CI schedules (OpenPLZ nightly import)

Nightly imports are implemented in `.gitlab-ci.yml` via a schedule-triggered job.

## Jobs

- `import_openplz_locations_manual`
  - `rules: when: manual`
  - Run on demand to seed/update the DB.

- `import_openplz_locations_nightly`
  - `rules: if $CI_PIPELINE_SOURCE == "schedule"`
  - Intended for cron-based refresh.

Both jobs:

- Run `alembic upgrade head`
- Execute `python scripts/import_openplz_locations.py --language de`

## Configure the schedule in GitLab UI

1. GitLab project → **CI/CD** → **Schedules**
2. Create schedule:
   - Name: `OpenPLZ Nightly Import`
   - Cron: pick an off-peak time (example: `0 2 * * *` for 2:00 UTC)
   - Target branch: `main` (or whichever branch deploys API)

After the schedule is created, GitLab will trigger `import_openplz_locations_nightly` based on `CI_PIPELINE_SOURCE == "schedule"`.

