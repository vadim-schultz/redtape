# Discovery online — production setup and first smoke test

Step-by-step guide to turn on scheduled discovery ingest after the **discovery-online**
suite is on `main`. Run this from a machine and network that can reach **Supabase**
(Postgres) and **GitHub**; corporate laptops that block outbound Postgres often cannot
issue API keys locally.

**Related:** [discovery-online.md](discovery-online.md) (operations) ·
[scheduled-jobs.md](scheduled-jobs.md) (calendar & secrets) ·
[deployment-checklist.md](deployment-checklist.md) (Render checklist) ·
[auth-setup.md](auth-setup.md) §7 (crawler keys)

**Production URLs (this repo):**

| Service | URL |
| --- | --- |
| API (Render) | `https://redtape-api.onrender.com` |
| Web (Workers) | `https://redtape-web.vadim-schultz.workers.dev` |
| Health check | `https://redtape-api.onrender.com/health` |

---

## Overview

| Layer | What you configure | Purpose |
| --- | --- | --- |
| **Render** (`redtape-api`) | `DISCOVERY_ADMIN_EMAILS` | Enables discovery (admin UI + machine API) in production |
| **Supabase + laptop** | `DATABASE_URL` (temporary) | Issue `DISCOVERY_API_KEY` into production `api_key` table |
| **GitHub Actions** | Repository secrets | Scheduled/manual ingest calls the live API |
| **GitHub Actions** | Manual workflow run | First smoke test (`job=discovery`) |

Discovery jobs **never** use `DATABASE_URL` in GHA. OpenPLZ days still need `DATABASE_URL`
as a GitHub secret (see [scheduled-jobs.md](scheduled-jobs.md)).

---

## Part 1 — Render (`redtape-api`)

### 1.1 Open the service

1. [Render Dashboard](https://dashboard.render.com) → service **`redtape-api`** (from
   [`render.yaml`](../../render.yaml)).
2. Confirm status **Live**. If cold, open `/health` in a browser or wait for
   [keep-alive](../../.github/workflows/keep-alive.yml).

### 1.2 Confirm existing variables

Under **Environment**, verify (do not commit these values):

| Variable | Expected |
| --- | --- |
| `DATABASE_URL` | Supabase connection string (usually **Session pooler**; see
  [`apps/api/.env.example`](../../apps/api/.env.example) § PostgreSQL) |
| `ENVIRONMENT` | `production` (from `render.yaml`) |
| `CORS_ALLOWED_ORIGINS` | Includes `https://redtape-web.vadim-schultz.workers.dev` |

Auth for the admin UI (if not already set): `SUPABASE_JWKS_URL`, `SUPABASE_JWT_ISSUER` per
[auth-setup.md](auth-setup.md) §4.

### 1.3 Add discovery admin allowlist

| Key | Value | Notes |
| --- | --- | --- |
| `DISCOVERY_ADMIN_EMAILS` | `you@example.com` | Comma-separated for multiple operators. Matching is case-insensitive. **Required** so `discovery_enabled` is true on the API (see [`config.py`](../../apps/api/app/config.py)). |
| `DISCOVERY_MACHINE_OPT_IN` | *(leave unset)* or `0` / `false` | Production: use the email allowlist. Set `1` only for local dev without allowlist. |

**Do not** set `DISCOVERY_API_URL` or `DISCOVERY_API_KEY` on Render — GHA uses GitHub
Secrets for those ([`render.yaml`](../../render.yaml) comments).

### 1.4 Deploy and verify health

Save environment → trigger **Manual Deploy** if Render does not redeploy automatically.

```bash
curl -sS https://redtape-api.onrender.com/health
```

Expect: `{"status":"ok"}` and HTTP `200`.

---

## Part 2 — Issue `DISCOVERY_API_KEY` (different computer / network)

The crawler key must be stored in the **production** database (hash in `api_key`). GHA
sends the plaintext key as `X-API-Key` to the live API.

### 2.1 Get `DATABASE_URL` (production)

**Render** → `redtape-api` → **Environment** → copy `DATABASE_URL`.

Or **Supabase** → Project → **Connect** → **Session pooler** URI:

- Use driver prefix `postgresql+psycopg://` (not plain `postgresql://`).
- Append `?sslmode=require` if missing.
- Prefer the **pooler** host if direct `db.<ref>.supabase.co` is IPv4-only on your network
  (see `.env.example`; ports are often **6543** session pooler or **5432** depending on mode).

Never commit or paste this URL into git.

### 2.2 Clone repo and use the **API** virtualenv

Work in **`apps/api`**, not `apps/`.

```bash
git clone https://github.com/vadim-schultz/redtape.git
cd redtape/apps/api
```

If `.venv` does not exist:

```bash
uv venv
uv pip install -e .
```

**Common mistake:** `ModuleNotFoundError: No module named 'pydantic'` means you ran
system `python` instead of:

```bash
.venv/bin/python -m scripts.issue_api_key ...
```

### 2.3 Issue the key

```bash
export DATABASE_URL='postgresql+psycopg://...'   # paste from Render / Supabase

.venv/bin/python -m scripts.issue_api_key --name discovery-scheduled-gha
```

**Output (copy immediately — shown once only):**

```text
issue_api_key: new key (copy it now, it will not be shown again): rt_<secret>
```

Store the full `rt_…` string in a password manager until it is in GitHub Secrets.

**Revoke later** (uses 8-character prefix after `rt_`):

```bash
.venv/bin/python -m scripts.issue_api_key --revoke <8-char-prefix>
```

See [auth-setup.md](auth-setup.md) §7.

### 2.4 Troubleshooting key issuance

| Symptom | What to try |
| --- | --- |
| Hangs with no output | Different network/VPN; verify pooler host/port; test with `psql` or Supabase SQL editor |
| `connection refused` / timeout | Firewall; try session pooler URI from dashboard |
| `ModuleNotFoundError` | Use `apps/api/.venv/bin/python`, run `uv pip install -e .` in `apps/api` |
| Wrong venv at `apps/.venv` | Remove mistaken venv: `rm -rf ../.venv`; only use `apps/api/.venv` |

---

## Part 3 — GitHub repository secrets

**GitHub** → repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**.

### 3.1 Required for discovery (smoke test + discovery days)

| Secret name | Value |
| --- | --- |
| `DISCOVERY_API_URL` | `https://redtape-api.onrender.com` |
| `DISCOVERY_API_KEY` | Full `rt_…` from Part 2 |
| `FEDERAL_JURISDICTION_ID` | `11111111-1111-1111-1111-111111111101` |

**`DISCOVERY_API_URL` rules:**

- **Host root only** — no `/api`, `/health`, or `/api/v1/discovery/machine`.
- Ingest client appends `/api/v1/discovery/machine/...`
  ([`api_client.py`](../../apps/discovery-ingest/discovery_ingest/api_client.py)).

### 3.2 Required for OpenPLZ maintenance days (`days % 6 == 0`)

| Secret name | Value |
| --- | --- |
| `DATABASE_URL` | Same production DB URL as Render (pooler recommended) |

Not used by the discovery job.

### 3.3 Optional overrides (defaults usually fine)

Only if you need non-default government endpoints
([`discovery_ingest/config.py`](../../apps/discovery-ingest/discovery_ingest/config.py)):

| Variable | Default |
| --- | --- |
| `GOVDATA_CKAN_BASE_URL` | `https://ckan.govdata.de/api/3/action` |
| `GOVDATA_PACKAGE_ID` | `ozg-leistungen-und-zugehorige-onlinedienste` |
| `PVOG_API_BASE_URL` | `https://pvog.fitko.net/suchdienst/api` |
| `FIM_PORTAL_BASE_URL` | `https://fimportal.de` |

---

## Part 4 — First smoke test (manual discovery run)

Forces **discovery** regardless of calendar ([`platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml)).

### 4.1 CLI (recommended)

On any machine with `gh` authenticated to the repo:

```bash
cd redtape   # your clone
gh workflow run platform-maintenance.yml -f job=discovery
gh run list --workflow=platform-maintenance.yml --limit 3
gh run watch <run-id>
```

### 4.2 GitHub UI

**Actions** → **Platform maintenance** → **Run workflow** → choose branch **`main`** →
**job:** `discovery` → **Run workflow**.

### 4.3 Expected job graph

1. **Resolve maintenance job** → selects `discovery` (forced by input).
2. **Discovery online (catalogue ingest)** runs (not “No maintenance job today”).
3. Steps, in order:
   - **Wait for Render API health** — polls `GET {DISCOVERY_API_URL}/health` (up to ~12×10s).
   - **GovData OZG catalogue fetch** — `govdata fetch --jurisdiction-id … --max-pages 150`.
   - **PVOG Suchdienst catalogue run** — `pvog run --max-pages 50`.
   - **Discovery worker drain** — `worker drain --max-tasks 50` (JSON on stdout).

### 4.4 Failure triage

| Symptom | Check |
| --- | --- |
| Workflow runs `skip` only | You forgot `-f job=discovery`; or wrong workflow |
| Health wait timeout | Render asleep; wrong `DISCOVERY_API_URL` (must be host root) |
| 401 / 403 on machine API | Key not in prod DB; revoked key; typo in secret |
| `Discovery is disabled` (503) | `DISCOVERY_ADMIN_EMAILS` empty on Render; redeploy |
| GovData / PVOG step failed | Step log; public APIs (no secrets in workflow) |
| Drain failed | Task URLs; lease reclaim — see [discovery-online.md](discovery-online.md) |

Re-running `job=discovery` the same day should be **idempotent** for staging (no unbounded duplicate tasks/claims).

### 4.5 Calendar (after smoke test)

Daily cron **02:00 UTC** uses [`maintenance_job_router.py`](../../scripts/maintenance_job_router.py)
with anchor **`2026-01-01`**. Discovery runs when `days_since_anchor % 6 == 3`. See
[scheduled-jobs.md](scheduled-jobs.md).

---

## Part 5 — Verify in the admin UI

1. Sign in on production with an email listed in `DISCOVERY_ADMIN_EMAILS`
   (Supabase magic link — [auth-setup.md](auth-setup.md)).
2. Open:
   - `https://redtape-web.vadim-schultz.workers.dev/admin/discovery/catalogue`
   - `https://redtape-web.vadim-schultz.workers.dev/admin/discovery/tasks`
3. After a green smoke run: catalogue rows and/or tasks should show recent ingest activity.

**Emit to suggestions** remains **manual** from the admin UI
([discovery-layer.md](discovery-layer.md)).

---

## Part 6 — Checklist (printable)

- [ ] Render: `DISCOVERY_ADMIN_EMAILS` set; `DISCOVERY_MACHINE_OPT_IN` unset; `/health` → 200
- [ ] Key issued: `.venv/bin/python -m scripts.issue_api_key --name discovery-scheduled-gha` against **production** `DATABASE_URL`
- [ ] GitHub secrets: `DISCOVERY_API_URL`, `DISCOVERY_API_KEY`, `FEDERAL_JURISDICTION_ID`
- [ ] (Optional) GitHub `DATABASE_URL` for OpenPLZ days
- [ ] `gh workflow run platform-maintenance.yml -f job=discovery` → green
- [ ] Admin UI: catalogue / tasks look sane
- [ ] Store `DISCOVERY_API_KEY` only in GitHub Secrets (never in git)

---

## Rotating `DISCOVERY_API_KEY`

1. Issue new key: `python -m scripts.issue_api_key --name discovery-scheduled-gha`
2. Update GitHub secret `DISCOVERY_API_KEY`
3. Run one successful `job=discovery`
4. Revoke old prefix: `python -m scripts.issue_api_key --revoke <prefix>`

[deployment-checklist.md](deployment-checklist.md) § Discovery · [auth-setup.md](auth-setup.md) §7.
