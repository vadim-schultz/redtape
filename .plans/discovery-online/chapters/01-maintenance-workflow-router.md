---
name: "Chapter 1 — Maintenance workflow router"
overview: "Unified platform-maintenance GHA workflow with 6-day OpenPLZ/discovery router; retire standalone openplz schedule."
todos:
  - id: workflow
    content: "Add .github/workflows/platform-maintenance.yml"
    status: pending
  - id: router
    content: "days_since_anchor % 6 router + workflow_dispatch inputs"
    status: pending
  - id: docs
    content: "Update scheduled-jobs.md"
    status: pending
isProject: false
---

# Chapter 1 — Maintenance workflow router

**Repo:** `redtape` · **Branch:** `feat/discovery-online-maintenance-workflow` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

One GitHub Actions workflow runs daily at 02:00 UTC, routes to OpenPLZ import on `days % 6 == 0` and discovery on `days % 6 == 3`, and no-ops otherwise. `workflow_dispatch` can force `openplz`, `discovery`, or `skip` for debugging. Replace the Mon+Thu schedule in [openplz-import.yml](../../../.github/workflows/openplz-import.yml) (remove schedule from old file or delete file after migration).

## Design decisions

**Anchor date:** `MAINTENANCE_ANCHOR_DATE=2026-01-01` (UTC) as env in workflow or documented constant in router script.

**OpenPLZ job steps** copy existing workflow: checkout, Python 3.12, `pip install -e .` in `apps/api`, `alembic upgrade head`, constraint check, `import_openplz_locations.py --language de`.

**Discovery job** is a placeholder step in this chapter (`echo` / `exit 0`) or calls a no-op script — full steps land in chapters 3–4, 7–8.

**No secrets in logs.** Mask `DATABASE_URL` and API keys.

## Files

| Path | Change |
| --- | --- |
| `.github/workflows/platform-maintenance.yml` | New unified workflow |
| `.github/workflows/openplz-import.yml` | Remove `schedule` or delete after cutover |
| `scripts/maintenance_job_router.py` | Optional pure router (testable) |
| `docs/operations/scheduled-jobs.md` | Document new cadence |
| `apps/api/tests/test_maintenance_job_router.py` | Router unit tests (if script extracted) |

## TDD loop

| Test | Asserts |
| --- | --- |
| `maintenance router · day 0 selects openplz` | Happy path |
| `maintenance router · day 3 selects discovery` | Happy path |
| `maintenance router · day 1 selects skip` | Negative / no-op path |
| `maintenance router · dispatch override forces discovery` | Input overrides calendar |

## Refactor gate

Router logic in one testable function; workflow YAML only calls it. Report outcome.

## Verification

```bash
./ci.sh
# Manual: gh workflow run platform-maintenance.yml -f job=openplz
```

## PR

Target `feat/plans-discovery-online` only.
