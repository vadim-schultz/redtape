---
name: "Chapter 2 — Secrets and URL canon"
overview: "Document GHA secrets, fix DISCOVERY_API_URL host-root canon in runbooks and ingest README."
todos:
  - id: docs
    content: "discovery-layer.md + discovery-ingest README + .env.example"
    status: pending
  - id: example
    content: "GHA secrets table in scheduled-jobs.md"
    status: pending
isProject: false
---

# Chapter 2 — Secrets and URL canon

**Repo:** `redtape` · **Branch:** `feat/discovery-online-secrets-canon` · **Status:** planned

**Depends on:** [1](01-maintenance-workflow-router.md) · **Decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md) D7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

Operators and GHA can configure discovery scheduled runs without path-doubling or missing secrets. `DISCOVERY_API_URL` is the **Render host root** (e.g. `https://redtape-api.onrender.com`); the client adds `/api/v1/discovery/machine/...`.

## Design decisions

**GHA repository secrets:**

| Secret | Example |
| --- | --- |
| `DATABASE_URL` | Supabase pooler URL (OpenPLZ job only) |
| `DISCOVERY_API_URL` | `https://redtape-api.onrender.com` |
| `DISCOVERY_API_KEY` | `rt_…` from `python -m scripts.issue_api_key --name discovery-scheduled-gha` |
| `FEDERAL_JURISDICTION_ID` | `11111111-1111-1111-1111-111111111101` |

**Optional workflow env:** `GOVDATA_CKAN_BASE_URL`, `PVOG_API_BASE_URL`, `FIM_PORTAL_BASE_URL` — defaults in [config.py](../../../apps/discovery-ingest/discovery_ingest/config.py).

## Files

| Path | Change |
| --- | --- |
| `docs/operations/discovery-layer.md` | Fix `DISCOVERY_API_URL` examples |
| `apps/discovery-ingest/README.md` | Host root + issue key steps |
| `docs/operations/scheduled-jobs.md` | Secrets table for both jobs |
| `docs/operations/deployment-checklist.md` | Cross-link discovery secrets |

## TDD loop

| Test | Asserts |
| --- | --- |
| `test_discovery_operations_runbook · DISCOVERY_API_URL documents host root` | Doc sync test (extend existing if present) |
| `test_govdata_cli · posts to /api/v1/discovery/machine/catalogue/batch on host root` | Already in ingest tests — keep green |

## Refactor gate

Docs-only chapter unless a small test asserts runbook strings. Report outcome.

## Verification

```bash
./ci.sh
```

## PR

Target loop branch.
