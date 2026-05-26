# Production Deployment Checklist

This checklist is intended for the **Wave 3 deployment**:
- Backend: Litestar API on **Render** (`/health` must work)
- Frontend: Vite/React SPA on **Cloudflare Pages**
- Free-tier friendliness: GitHub Actions keep-alive prevents Render from sleeping during use

Update the stored service URLs if you change project/service names.

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
- [ ] No CORS errors from `https://<frontend>.pages.dev` (or configured frontend origin).

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

