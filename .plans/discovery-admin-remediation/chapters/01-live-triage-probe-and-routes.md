---
name: "Chapter 1 — Live triage: probe and routes"
overview: "Record the real HTTP status of the discovery admin probe and confirm the blank-page cause before any menu code."
todos:
  - id: probe-status
    content: "Browser and curl status of GET admin/tasks?limit=1 for the operator account"
    status: pending
  - id: render-env
    content: "Render env names: DISCOVERY_ADMIN_EMAILS, auth enabled, DISCOVERY_MACHINE_OPT_IN"
    status: pending
  - id: local-repro
    content: "Local run reproduces the blank page and the router warning"
    status: pending
  - id: record
    content: "Triage note in run-ledger and discovery-layer runbook"
    status: pending
isProject: false
---

# Chapter 1 — Live triage: probe and routes

**Repo:** `redtape` · **Branch:** `docs/discovery-admin-remediation-triage` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §2 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-remediation` · **Release branch:** `main`

## Goal

Pick the actual cause of the missing menu links (F3) with one HTTP status, and confirm the blank pages (F1) in a real browser, before any code changes. The outcome is a short triage note and a go/no-go for the cause-specific part of chapter 3.

This chapter is ops-first. The implementer prepares the checklist and the note; the **operator** runs the steps that need a bearer token or dashboard access. Never print, log, or commit tokens or secret values.

## Operator steps

1. **Browser probe status.** Signed in as the admin, open devtools → Network, open the menu, and read the status of `GET /api/v1/discovery/admin/tasks?limit=1`. Note whether the request was sent at all (no request = `status` is not `authenticated` or no `accessToken`).
2. **Curl through both origins** (token from devtools; do not paste it into chat or files):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" \
  "https://<web-origin>/api/v1/discovery/admin/tasks?limit=1"
curl -sS -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" \
  "https://redtape-api.onrender.com/api/v1/discovery/admin/tasks?limit=1"
```

| Web origin | Render direct | Reading |
| --- | --- | --- |
| same | same | API outcome; worker proxy is fine |
| differs | — | Worker proxy or Cloudflare config problem |

| HTTP | Cause (see architecture F3) |
| --- | --- |
| 200 | Probe works; investigate the bundle/menu (step 5) |
| 403 | Email not on `DISCOVERY_ADMIN_EMAILS` |
| 401 | Auth disabled or JWT verification misconfigured on Render |
| 503 | Discovery disabled, or cold-start/proxy 503 (repeat after `/health` is warm) |
| 5xx / timeout | Cold start or API fault; check Render logs |

3. **Render environment (names and booleans only).** `DISCOVERY_ADMIN_EMAILS` contains the exact email of the Supabase login (comparison is lowercase); auth is enabled; state of `DISCOVERY_MACHINE_OPT_IN`. Reference: [`guards.py`](../../../apps/api/app/features/discovery/guards.py), [`config.py`](../../../apps/api/app/config.py), [`render.yaml`](../../../render.yaml).
4. **Local reproduction of F1.** Start the API with `DISCOVERY_ADMIN_EMAILS=<operator email>` and Supabase auth configured, run `npm run dev` in `apps/web`, sign in, and open `/admin/discovery/catalogue`. Expected on the current code: blank body and the console warning `No routes matched location "/admin/discovery/catalogue"`. This run also isolates the guard question: with the allowlist set locally, only the route defect remains.
5. **Deployed bundle.** Confirm Cloudflare serves the current `main` build (compare the asset hashes in the page source with a fresh `npm run build`, or the Cloudflare deployment record). The Browse/Suggest icons already prove the chapter-4 bundle of the previous suite is live.

## Files

| Path | Change |
| --- | --- |
| [`docs/operations/discovery-layer.md`](../../../docs/operations/discovery-layer.md) | Triage table: probe status → cause → fix (feeds the troubleshooting entry in chapter 4) |

## TDD loop

Ops chapter — no production code. If the runbook is covered by a doc test, follow the pattern in `apps/api/tests/test_discovery_operations_runbook.py`.

## Verification

- Triage note recorded in the run ledger **blocker** column for chapter 3: probe status for the operator account, which cause applies, and whether a Render config fix is needed (operator action).
- The local reproduction outcome (blank page, warning present or not) is recorded.
- No `./ci.sh` required unless the docs PR touches tested markdown.

## Git workflow

```bash
git checkout feat/plans-discovery-admin-remediation && git pull
git checkout -b docs/discovery-admin-remediation-triage
```

```text
docs(discovery): record admin probe triage
```

Open the chapter PR into `feat/plans-discovery-admin-remediation`, not `main`.
