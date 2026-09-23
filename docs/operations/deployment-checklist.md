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
- [ ] No CORS errors from `https://redtape-web.vadim-schultz.workers.dev` (or configured frontend origin — check `render.yaml`'s `CORS_ALLOWED_ORIGINS`).

How to troubleshoot quickly:
- [ ] Check Render logs for startup/DB connection/a​lembic migration failures.
- [ ] Confirm `DATABASE_URL` works from Render environment (Supabase session pooler recommended).

---

## Frontend (Cloudflare Pages)

Prereqs:
- Cloudflare Pages project is connected to the repo.
- `VITE_API_URL` env var points at the Render API base URL.

Checks:
- [ ] Cloudflare Pages shows the latest commit deployed successfully.
- [ ] Opening the production URL shows no white-screen errors.
- [ ] Locale switcher changes UI language (if implemented in the current wave).
- [ ] Visiting `/documents` shows localized document titles.
- [ ] Visiting `/documents/{id}` shows the dependency list.
- [ ] Browser DevTools → Network shows API calls succeed (`200`s), not CORS blocks.

---

## Keep-Alive Automation (Render Free Tier)

Prereqs:
- Keep-alive GitHub workflow is added and enabled.

Checks:
- [ ] GitHub Actions workflow ran recently and `curl` to `/health` succeeds.
- [ ] Render service remains awake during your testing window (at least 15–30 minutes).
- [ ] GitHub Actions usage stays within free-tier monthly minutes.

