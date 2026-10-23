---
name: "Chapter 2 — Retire keep-alive and the legacy OpenPLZ workflow"
overview: "Delete keep-alive.yml and openplz-import.yml and every reference to them; an external pinger replaces the keep-alive."
todos:
  - id: delete
    content: "Delete the two workflow files"
    status: pending
  - id: refs
    content: "Remove or rewrite every reference in docs and render.yaml"
    status: pending
isProject: false
---

# Chapter 2 — Retire keep-alive and the legacy OpenPLZ workflow

**Repo:** `redtape` (`.github/workflows`, `docs`, `render.yaml`) · **Branch:** `chore/gha-budget-retire-workflows` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Decisions:** D1, D5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `chore/gha-budget`

## Goal

`keep-alive.yml` cost 98 min in October and does not work: GitHub cron fires roughly every three hours, Render's free tier sleeps after 15 minutes, and `/health` never touches the database. `openplz-import.yml` is a `workflow_dispatch`-only duplicate of the `openplz` job in `platform-maintenance.yml`; its 291 October minutes came from its old schedule, which is already gone. Delete both.

## Design

1. `git rm .github/workflows/keep-alive.yml .github/workflows/openplz-import.yml`.
2. Find every reference: `grep -rn "keep-alive\|keep_alive\|openplz-import.yml\|OpenPLZ Import\|Keep Render" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.plans .` and fix each:
   - `docs/operations/deployment-checklist.md` (top bullet, and the "Keep-Alive Automation (Render Free Tier)" section): replace with an "External pinger" section: create a free UptimeRobot (5 minute interval) or cron-job.org monitor on `https://redtape-api.onrender.com/health`, ideally limited to browsing hours; note the free tier cold-starts after 15 idle minutes and that this costs zero Actions minutes.
   - `docs/planning/STATUS.md` line 15 (Wave 3 row): replace the keep-alive link with the deployment checklist section; keep the rest of the row.
   - `render.yaml` comment "Health endpoint used by Render + GitHub keep-alive." → "Health endpoint used by Render and the external pinger." (comment only).
   - `docs/operations/scheduled-jobs.md`: delete the paragraph about the legacy OpenPLZ workflow and the "Render keep-alive ping (separate)" bullet under Related; manual OpenPLZ runs are `gh workflow run platform-maintenance.yml -f job=openplz`.
   - `docs/operations/openplz-import.md`, `docs/operations/discovery-online-production-setup.md` and `apps/discovery-ingest/README.md`: fix mentions that point at the deleted files or at the keep-alive.
3. Leave `.plans/**` historical text untouched (plans are records), except nothing needs editing there.

## Tests

No unit harness. Gate: actionlint on the remaining workflows; the `grep` above finds no reference outside `.plans/`; `render.yaml` still parses (`python3 -c "import yaml;yaml.safe_load(open('render.yaml'))"`).

## Refactor gate

Audit that `docs/operations/scheduled-jobs.md` does not describe the same cadence in two places. Record the outcome.

## Commits

- `ci: remove the GitHub keep-alive workflow`
- `ci: remove the duplicate OpenPLZ import workflow`
- `docs(ops): replace keep-alive with an external pinger and fix references`
