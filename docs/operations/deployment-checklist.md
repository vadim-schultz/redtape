# Production Deployment Checklist

This checklist is intended for the **Wave 3 deployment**:
- Backend: Litestar API on **Render** (`/health` must work)
- Frontend: Vite/React SPA on **Cloudflare Pages**
- Free-tier friendliness: GitHub Actions keep-alive prevents Render from sleeping during use

Update the stored service URLs if you change project/service names.

> **Last verified: 2026-09-22.** `render.yaml`, CORS config, and the keep-alive workflow are committed.
> - `https://redtape-api.onrender.com/health` returns `{"status":"ok"}` after the Render free-tier cold start. The August 2026 HTTP 503 with `Retry-After` was the service asleep.
> - `https://redtape-web.pages.dev` is the planned Cloudflare Pages hostname and is **not reachable**. The Pages project was never created (Wave 3 D5–D6). CORS and env examples already name this origin.
>
> See [STATUS.md](../planning/STATUS.md). Re-run the checks below once a Pages project exists, then update this note.

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

### One-time setup (Wave 3 D5–D6)

Create the project in the [Cloudflare dashboard](https://dash.cloudflare.com/) (Workers & Pages → Create → Pages → Connect to Git):

| Setting | Value |
|---------|--------|
| Git repository | `vadim-schultz/redtape` |
| Project name | `redtape-web` (hostname `https://redtape-web.pages.dev`) |
| Production branch | `main` |
| Root directory | `apps/web` |
| Build command | `npm run build` (or `npm install --no-audit --no-fund && npm run build` if install fails) |
| Build output directory | `dist` |

Production environment variables (required before the first successful build):

| Name | Value |
|------|--------|
| `NODE_VERSION` | `22` |
| `VITE_API_URL` | `https://redtape-api.onrender.com` (no trailing slash) |

Do not rely on preview deployments for API smoke tests: preview hostnames are not in the API CORS allow list.

The repo includes [`apps/web/public/_redirects`](../../apps/web/public/_redirects) so client routes (`/documents`, `/documents/:id`) work on refresh.

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

