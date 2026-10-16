# Production Deployment Checklist

This checklist is intended for the **Wave 3 deployment**:
- Backend: Litestar API on **Render** (`/health` must work)
- Frontend: Vite/React SPA on **Cloudflare Pages**
- Free-tier friendliness: GitHub Actions keep-alive prevents Render from sleeping during use

Update the stored service URLs if you change project/service names.

> **Last verified: 2026-08-22.** `render.yaml`, CORS config, and the keep-alive workflow are all committed and correctly wired, but nothing below was confirmed live from this repo's evidence alone:
> - `https://redtape-api.onrender.com/health` returned **HTTP 503 with `Retry-After`** on two direct checks — consistent with a real Render service that exists but is asleep/cold (free tier) or currently unhealthy. Not confirmed as a working `200 {"status":"ok"}`.
> - `https://redtape-web.pages.dev` **failed DNS resolution entirely** (`ENOTFOUND`) — this Cloudflare Pages project does not appear to exist right now. Treat the frontend as **not deployed** until a Pages project is actually created and connected (Wave 3 steps D5–D6 look undone in practice, even though CORS/env-var config for it is already in place).
>
> See [STATUS.md](../planning/STATUS.md) for the current live-status summary. Re-run this checklist for real once a Pages project exists and the Render service has been woken/checked from a normal browser, then update this note.

> **Update, 2026-09-23:** the frontend is now deployed, but under `https://redtape-web.vadim-schultz.workers.dev` — a `workers.dev` domain, not the `pages.dev` domain assumed above and throughout this checklist. That mismatch broke CORS between the two hosts (fixed in `render.yaml` and `apps/api/app/middleware/cors.py`; see [STATUS.md](../planning/STATUS.md) for details). This checklist still needs a real run against both live URLs once the CORS fix is confirmed deployed.

---

## Backend (Render)

Prereqs:
- Render service is created and uses the `render.yaml` build/start commands.
- `DATABASE_URL` is configured in Render Environment variables.

Checks:
- [ ] Render service is in **Live** state.
- [ ] `GET /health` returns `200` and JSON:
  - `{"status":"ok"}`
- [ ] `GET /api/v1/locales` includes `de` and `en`.
- [ ] `GET /api/v1/translations?locale=de` returns a JSON bundle (non-empty).
- [ ] `GET /api/v1/documents` returns the MVP slice (expected 4 documents seeded).
- [ ] `GET /api/v1/documents/{id}` returns:
  - Localized `title` and `description`
  - `requirements[]` (3 direct dependencies)
- [ ] `CORS_ALLOWED_ORIGINS` in `render.yaml` still includes the Workers origin (for direct API clients). Production browser traffic should be **same-origin** via the Worker proxy, not cross-origin to Render.

### Discovery (Render environment)

Set these in the Render dashboard for `redtape-api` (not in `render.yaml` — see comments there). Canon:
[`discovery-layer.md`](discovery-layer.md).

Prereqs:

- [ ] `DISCOVERY_ADMIN_EMAILS` lists comma-separated operator emails (lowercase is normalized). Discovery admin routes and `/admin/discovery/*` stay off until this is non-empty (unless you intentionally enable dev-only opt-in).
- [ ] `DISCOVERY_MACHINE_OPT_IN` is **unset** or `0`/`false` in production when the allowlist is set (leave opt-in for local dev only).
- [ ] GitHub Actions discovery secrets match [`scheduled-jobs.md`](scheduled-jobs.md) (`DISCOVERY_API_URL` as **host root**, `DISCOVERY_API_KEY`, `FEDERAL_JURISDICTION_ID`).

Checks (no laptop ingest required):

- [ ] Allowlisted user signs in on production and can open `/admin/discovery/tasks` (queue / pipeline UI).
- [ ] **Platform maintenance** discovery job succeeds (Actions → **Platform maintenance**, or `gh workflow run platform-maintenance.yml -f job=discovery`).
- [ ] After a scheduled or manual discovery run, the admin catalogue view shows recent ingest activity (tasks or pipeline events).

**Rotate `DISCOVERY_API_KEY` (GHA):** issue a new key with
`python -m scripts.issue_api_key --name discovery-scheduled-gha` (`apps/api`), update the GitHub secret, run one
successful discovery job, then revoke the old prefix per
[`auth-setup.md` §7](auth-setup.md#7-issue-and-revoke-crawler-keys).

How to troubleshoot quickly:
- [ ] Check Render logs for startup/DB connection/a​lembic migration failures.
- [ ] Confirm `DATABASE_URL` works from Render environment (Supabase session pooler recommended).
- [ ] If logs show `DuplicateObject: type "discovery_source" already exists` and discovery
  tables already exist, verify schema (`alembic check` with session/direct URL), then
  `alembic stamp 20261012_discovery_staging` or deploy migration hardening from `main`.

---

## Frontend (Cloudflare Pages)

Prereqs:
- Cloudflare Workers Build project is connected to the repo (serves `https://redtape-web.vadim-schultz.workers.dev`).
- [`apps/web/wrangler.jsonc`](../../apps/web/wrangler.jsonc) defines `main` (`src/worker.ts`), `assets.run_worker_first` for `/api/*`, and `API_ORIGIN` (`vars` + `previews.vars`) pointing at the Render API — **not** dashboard-only; git-triggered builds sync from the repo.

Checks:
- [ ] Cloudflare shows the latest commit deployed successfully.
- [ ] Opening the production URL shows no white-screen errors.
- [ ] Locale switcher changes UI language (if implemented in the current wave).
- [ ] Visiting `/documents` shows localized document titles.
- [ ] Visiting `/documents/{id}` shows the dependency list.
- [ ] Browser DevTools → Network shows same-origin API calls to `https://redtape-web.vadim-schultz.workers.dev/api/v1/…` with `200`s (not direct `redtape-api.onrender.com` from the browser).

---

## GitHub Actions — platform maintenance

Prereqs:
- Unified workflow [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml) is enabled.

Checks:
- [ ] Repository secrets for OpenPLZ and discovery jobs match [`scheduled-jobs.md`](scheduled-jobs.md) (`DATABASE_URL`, `DISCOVERY_API_URL` as **host root**, `DISCOVERY_API_KEY`, `FEDERAL_JURISDICTION_ID`).
- [ ] `DISCOVERY_API_KEY` was issued with `python -m scripts.issue_api_key --name discovery-scheduled-gha` and stored only in GitHub Secrets (not in git).

---

## Keep-Alive Automation (Render Free Tier)

Prereqs:
- Keep-alive GitHub workflow is added and enabled.

Checks:
- [ ] GitHub Actions workflow ran recently and `curl` to `/health` succeeds.
- [ ] Render service remains awake during your testing window (at least 15–30 minutes).
- [ ] GitHub Actions usage stays within free-tier monthly minutes.

