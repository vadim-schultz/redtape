# Production Deployment Checklist

This checklist is intended for the **Wave 3 deployment**:
- Backend: Litestar API on **Render** (`/health` must work)
- Frontend: Vite/React SPA on **Cloudflare Pages**
- Free-tier friendliness: an external pinger (see [External pinger](#external-pinger-render-free-tier)) keeps Render from sleeping during use

Update the stored service URLs if you change project/service names.

> **Last verified: 2026-08-22.** `render.yaml` and the CORS config are committed and correctly wired, but nothing below was confirmed live from this repo's evidence alone:
> - `https://redtape-api.onrender.com/health` returned **HTTP 503 with `Retry-After`** on two direct checks — consistent with a real Render service that exists but is asleep/cold (free tier) or currently unhealthy. Not confirmed as a working `200 {"status":"ok"}`.
> - `https://redtape-web.pages.dev` **failed DNS resolution entirely** (`ENOTFOUND`) — this Cloudflare Pages project does not appear to exist right now. Treat the frontend as **not deployed** until a Pages project is actually created and connected (Wave 3 steps D5–D6 look undone in practice, even though CORS/env-var config for it is already in place).
>
> See [STATUS.md](../planning/STATUS.md) for the current live-status summary. Re-run this checklist for real once a Pages project exists and the Render service has been woken/checked from a normal browser, then update this note.

> **Update, 2026-09-23:** the frontend is now deployed, but under `https://redtape-web.vadim-schultz.workers.dev` — a `workers.dev` domain, not the `pages.dev` domain assumed above and throughout this checklist. That mismatch broke CORS between the two hosts (fixed in `render.yaml` and `apps/api/app/middleware/cors.py`; see [STATUS.md](../planning/STATUS.md) for details). This checklist still needs a real run against both live URLs once the CORS fix is confirmed deployed.

> **Read-only validation, 2026-11-06:** the deployed web shell returned `200` and the isolated API
> check returned `GET /health` `200 {"status":"ok"}`. The deployed API does not yet contain the
> category-taxonomy cutover: `GET /api/v1/categories` returned `404`, the category-filtered
> candidate request returned `422`, and an unfiltered candidate read still exposed the retired
> `domains`/`situations` fields. `/api/v1/documents` returned `200` with an empty list. Treat the
> category, chip, accordion, and PVOG-provenance live checks as pending until the C9 release is
> deployed; this run performed no writes.

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
- [ ] `GET /api/v1/candidates?limit=1` returns `200` with `{items, total, offset, limit}`; the item carries
  `confidence` and canonical `categories` entries with `confidence`. This is the list behind `/documents`.
- [ ] `GET /api/v1/candidates?sort_by=confidence&sort_order=desc&limit=5` returns `200` with `confidence` non-increasing.
- [ ] `GET /api/v1/documents` returns `200` (dormant: the sample documents are no longer seeded and the web list no longer reads it; `total` stays `0` because nothing in the browse flow promotes a candidate).
- [ ] `CORS_ALLOWED_ORIGINS` in `render.yaml` still includes the Workers origin (for direct API clients). Production browser traffic should be **same-origin** via the Worker proxy, not cross-origin to Render.

### Discovery (Render environment)

Full step-by-step (Render, GitHub secrets, API key from another network, smoke test):
[discovery-online-production-setup.md](discovery-online-production-setup.md).

Set these in the Render dashboard for `redtape-api` (not in `render.yaml` — see comments there). Canon:
[`discovery-layer.md`](discovery-layer.md).

Prereqs:

- [ ] `DISCOVERY_ADMIN_EMAILS` lists comma-separated operator emails (lowercase is normalized). Discovery admin routes and `/admin/discovery/*` stay off until this is non-empty (unless you intentionally enable dev-only opt-in).
- [ ] `DISCOVERY_MACHINE_OPT_IN` is **unset** or `0`/`false` in production when the allowlist is set (leave opt-in for local dev only).
- [ ] GitHub Actions discovery secrets match [`scheduled-jobs.md`](scheduled-jobs.md) (`DISCOVERY_API_URL` as **host root**, `DISCOVERY_API_KEY`, `FEDERAL_JURISDICTION_ID`).
- [ ] `FEDERAL_JURISDICTION_ID` equals production `jurisdiction.id` for `kind=COUNTRY`, `code=DE` (not the seed placeholder when OpenPLZ has run) — SQL or [`print_federal_jurisdiction_id.py`](../../apps/api/scripts/print_federal_jurisdiction_id.py); see [discovery-online.md](discovery-online.md) § Catalogue batch 500 triage.

Checks (no laptop ingest required):

- [ ] Allowlisted user signs in on production and can open `/admin/discovery/tasks` (queue / pipeline UI).
- [ ] **Platform maintenance** discovery job succeeds (Actions → **Platform maintenance**, or `gh workflow run platform-maintenance.yml -f job=discovery`).
- [ ] After a scheduled or manual discovery run, the admin catalogue view shows recent ingest activity (tasks or pipeline events).

### Object store, budget caps and Cloudflare (Render environment)

The crawl layer stores rendered snapshots and screenshots in Cloudflare R2 through its S3 API. Set the variables in the
Render dashboard for `redtape-api`, never in `render.yaml` (it is committed; the file only has a comment).
Step by step: [crawlers-operator-checklist.md](crawlers-operator-checklist.md) S1 to S4 and S21.

| Variable | Value |
| --- | --- |
| `OBJECT_STORE_ENDPOINT_URL` | `https://<account_id>.r2.cloudflarestorage.com` (the S3 endpoint, not a custom domain) |
| `OBJECT_STORE_REGION` | `auto` |
| `OBJECT_STORE_BUCKET` | The private bucket, for example `discovery-artifacts` |
| `OBJECT_STORE_ACCESS_KEY_ID`, `OBJECT_STORE_SECRET_ACCESS_KEY` | An R2 token with Object Read & Write on that bucket only |
| `OBJECT_STORE_FORCE_PATH_STYLE` | Optional, default `true` |
| `OBJECT_STORE_MAX_BYTES` | Optional, default 9500000000 (95 percent of R2's free 10 GB) |

All five required values must be set. If one is missing, the API still boots, the artifact routes answer **503**, and
a browser drain refuses to start. An upload that would pass `OBJECT_STORE_MAX_BYTES` answers **507** and writes
nothing. The cap sums the `discovery_artifact` rows, not the objects in the bucket.

The budget ledger caps every free allocation at 95 percent of its allowance. The defaults are already safe, so set a
variable only to tighten it.

| Variable | Default | Guards |
| --- | --- | --- |
| `BUDGET_R2_CLASS_A_MONTHLY` | 950000 | R2 writes a month (free tier 1 million) |
| `BUDGET_R2_CLASS_B_MONTHLY` | 9500000 | R2 reads a month (free tier 10 million); each presigned link reserves one |
| `BUDGET_BROWSER_SECONDS_DAILY` | 570 | Cloudflare browser seconds a day, all runs together (free plan 600) |
| `BUDGET_NEURONS_DAILY` | 9500 | Workers AI neurons a day, an API variable (`llm_extract` and `llm eval` reserve from it; free plan 10,000). Cloudflare's own allocation also counts uses the ledger never sees, such as `llm probe`, so only 500 neurons a day stay unreserved; tighten it if other workloads use Workers AI |
| `BUDGET_ACTIONS_MINUTES_MONTHLY` | 2000 | This repository's GitHub Actions minutes a month |
| `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY` | 1900000 | Azure AI Translator characters a month (free tier F0 2 million). Nothing reserves from it until the Azure translation engine is deployed |
| `ACTIONS_CI_RESERVE_MINUTES` | 1000 | The part of those minutes that CI keeps; drains may use 1000 |
| `DB_SOFT_LIMIT_BYTES` | 475000000 | Database size above which machine writes that create rows answer 507 (Supabase goes read-only at 500 MB) |

- [ ] Render dashboard sets `BUDGET_ACTIONS_MINUTES_MONTHLY=2000` and `ACTIONS_CI_RESERVE_MINUTES=1000` for `redtape-api`, matching the new split above. This assumes this repository's share of the account-wide shared Actions-minutes pool has grown to 2,000 (unverified — see [`discovery-throughput/gaps-and-decisions.md`](../../.plans/discovery-throughput/gaps-and-decisions.md) D1); confirm the account pool really has this headroom before relying on it.

The Cloudflare Browser Run token (`CLOUDFLARE_BROWSER_API_TOKEN`, with `CLOUDFLARE_ACCOUNT_ID`) is deliberately
**not a Render variable**. The API never calls Cloudflare Browser Run. The token lives in GitHub Actions secrets and
in the operator's local environment, and has only the "Browser Run - Edit" permission.

The Workers AI token (`CLOUDFLARE_AI_API_TOKEN`, with `CLOUDFLARE_ACCOUNT_ID`) is likewise deliberately **not a Render
variable**. The API never calls Workers AI and never sees the token: the worker calls the model, and the API only keeps
the neuron ledger and the staged results. It lives in GitHub Actions secrets (used by `discovery-llm.yml` and
`discovery-llm-probe.yml` only) and in the operator's local environment, with only the Workers AI permission. The account
stays on the Workers **Free** plan (no Workers Paid, which would bill neurons).

**Deploy the API and the web app together.** The admin Coverage screen requires the `llm_outcomes` block that the API
now returns, so a new web deploy against an old API breaks that screen. After the deploy the API seeds translations on
boot (`apps/api/scripts/start.sh`); confirm the new keys under `discovery_admin.coverage.llm` exist. The extraction
migration `20261029_staging_edges` is additive and was applied to production by hand on 2026-10-28.
The document-browse-confidence release adds the data migration `20261102_remove_seeded_documents`, which deletes
the four seeded sample documents and their three requirement rows by exact id (irreversible; a promoted document
is kept). It runs on boot before the seed step, and `start.sh` no longer seeds documents.

Checks:

- [ ] `curl -s -w "\nHTTP %{http_code}\n" -H "X-API-Key: $DISCOVERY_API_KEY" "$DISCOVERY_API_URL/api/v1/discovery/machine/artifacts/status"` returns 200 with `"storage_enabled": true`.
- [ ] The same call to `…/machine/budgets` returns six resources (`r2_class_a`, `r2_class_b`, `browser_seconds`, `neurons`, `actions_minutes`, `azure_translator_chars`) with their caps.
- [ ] `GET …/machine/taxonomy` returns 200 with the active canonical category vocabulary.
- [ ] The storage probe passes (S6). It runs on a laptop with the Render values exported: `cd apps/api && set -a; source <env file>; set +a; .venv/bin/python -m scripts.object_store_probe`. Do not commit the env file.

### Worker-origin discovery probe sequence

Run the direct Render health check before browser checks. Production browser traffic is same-origin
through the Worker proxy; do not treat an HTML cold-start page as an API response.

1. `GET /health` on `https://redtape-api.onrender.com` returns HTTP `200` and application JSON.
2. From the Worker origin, request
   `/api/v1/discovery/admin/tasks?limit=1&offset=0` without a bearer token. The expected response is
   HTTP `401`.
3. Repeat the same Worker-origin probe with a valid session token for a non-allowlisted user. The
   expected response is HTTP `403`.
4. Repeat it with a valid session token for an allowlisted user. The expected response is HTTP `200`
   with valid JSON (`items`, `total`, `offset`, and `limit`).
5. With the same allowlisted bearer token, request
   `/api/v1/discovery/admin/coverage`. Expect HTTP `200` and valid JSON containing `by_source`,
   `tasks_pending`, `tasks_failed`, `emit_ready_count`, `task_counts`, `fetch_attempts_total`,
   `stale_claims`, `stale_runs`, `failures_by_source`, and `last_successful_run`.
6. With the same token, request
   `/api/v1/discovery/admin/catalogue?limit=50&offset=0`. Expect HTTP `200` and valid JSON containing
   `items`, `summary`, `total`, `offset`, and `limit`.

For authenticated requests, use the Worker origin and preserve the header:

```bash
curl -i \
  -H "Authorization: Bearer <session-token>" \
  "https://redtape-web.vadim-schultz.workers.dev/api/v1/discovery/admin/coverage"
```

Interpret failures in this order:

| Response | Meaning and action |
| --- | --- |
| `401` | Session is missing or expired; sign in again. |
| `403` | The session email is not in `DISCOVERY_ADMIN_EMAILS`; do not add a client-side allowlist. |
| `503` | Discovery is disabled or the API is still cold-starting; wait for `/health` and retry. |
| HTML, network failure, or invalid JSON | The request did not complete the Worker-to-Render API path; inspect Worker routing, Render logs, and the browser Network panel. |

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
- [ ] Visiting `/documents` renders candidate-backed cards with localized titles and a confidence circle; search and the confidence/title/newest sort change the order, and `/candidates` redirects to `/documents`.
- [ ] Browser DevTools → Network shows same-origin API calls to `https://redtape-web.vadim-schultz.workers.dev/api/v1/…` with `200`s (not direct `redtape-api.onrender.com` from the browser).

---

## GitHub Actions — platform maintenance

Prereqs:
- Unified workflow [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml) is enabled.

Checks:
- [ ] Repository secrets for OpenPLZ and discovery jobs match [`scheduled-jobs.md`](scheduled-jobs.md) (`DATABASE_URL`, `DISCOVERY_API_URL` as **host root**, `DISCOVERY_API_KEY`, `FEDERAL_JURISDICTION_ID` set from live DE country row per [discovery-online-production-setup.md](discovery-online-production-setup.md) §3.1).
- [ ] `DISCOVERY_API_KEY` was issued with `python -m scripts.issue_api_key --name discovery-scheduled-gha` and stored only in GitHub Secrets (not in git).
- [ ] The five drain workflows [`discovery-drain.yml`](../../.github/workflows/discovery-drain.yml), [`discovery-render.yml`](../../.github/workflows/discovery-render.yml), [`discovery-extract.yml`](../../.github/workflows/discovery-extract.yml), [`discovery-llm.yml`](../../.github/workflows/discovery-llm.yml) and [`discovery-screenshot.yml`](../../.github/workflows/discovery-screenshot.yml) exist on `main` (`gh workflow run` answers 404 for a workflow file that is not on `main` yet; all five and the probe workflows arrive with the release). Their schedule variables `DISCOVERY_DRAIN_SCHEDULE`, `DISCOVERY_RENDER_SCHEDULE`, `DISCOVERY_EXTRACT_SCHEDULE` and `DISCOVERY_SCREENSHOT_SCHEDULE` stay unset until [crawlers-operator-checklist.md](crawlers-operator-checklist.md) S13; `DISCOVERY_LLM_SCHEDULE` additionally waits on the extraction live gate ([extraction-operator-checklist.md](extraction-operator-checklist.md) OP14).
- [ ] Probe secrets: the five `OBJECT_STORE_*` secrets are used only by `discovery-storage-probe.yml`; `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_BROWSER_API_TOKEN` only by `discovery-render.yml` and `discovery-browser-probe.yml`.

---

## External pinger (Render free tier)

The Render free tier cold-starts after 15 idle minutes. A free external monitor keeps the API warm and costs zero GitHub Actions minutes (GitHub cron is best-effort and bills each run).

Prereqs:
- A free [UptimeRobot](https://uptimerobot.com) (5 minute interval) or [cron-job.org](https://cron-job.org) account.

Setup:
- Create an HTTP monitor on `https://redtape-api.onrender.com/health`, ideally limited to browsing hours.

Checks:
- [ ] The monitor reports the endpoint as up (`200 {"status":"ok"}`).
- [ ] Render service remains awake during your testing window (at least 15–30 minutes).
