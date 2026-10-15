---
name: "Chapter 4 — Scheduled catalogue ingest"
overview: "Wire discovery job in platform-maintenance: govdata fetch + pvog run with timeouts and reports."
todos:
  - id: workflow
    content: "Discovery job steps in platform-maintenance.yml"
    status: pending
  - id: pvog
    content: "pvog run limits --max-pages if needed"
    status: pending
  - id: health
    content: "API health retry before ingest"
    status: pending
isProject: false
---

# Chapter 4 — Scheduled catalogue ingest

**Repo:** `redtape` · **Branch:** `feat/discovery-online-scheduled-ingest` · **Status:** planned

**Depends on:** [3](03-govdata-live-fetch-cli.md), [5](05-ingest-idempotency.md) (may merge after 5 for safe re-runs — see rollout: implement 5 before enabling schedule in prod) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

The discovery branch of `platform-maintenance.yml` installs `apps/discovery-ingest`, exports secrets, retries Render `/health`, runs `govdata fetch` and `pvog run` for the federal jurisdiction, and exits non-zero on hard failures.

## Design decisions

**Order:** health check → govdata fetch → pvog run (both may be partial if timeboxed).

**Timeout:** `timeout-minutes: 90` on discovery job if needed; document caps.

**Depends on chapter 5** before treating production schedule as safe — until then, workflow may run on `workflow_dispatch` only.

**No `DATABASE_URL`** in discovery job env.

## Files

| Path | Change |
| --- | --- |
| `.github/workflows/platform-maintenance.yml` | Discovery job implementation |
| `apps/discovery-ingest/discovery_ingest/cli.py` | Optional `--max-pages` on pvog |
| `apps/discovery-ingest/discovery_ingest/health.py` | `wait_for_api(base_url)` with retries |
| `apps/discovery-ingest/tests/test_api_health.py` | Health waiter tests |

## TDD loop

| Test | Asserts |
| --- | --- |
| `wait_for_api · returns when health 200` | Happy path |
| `wait_for_api · raises after max retries on 503` | Negative path |

## Refactor gate

Health waiter separate from CLI. Report outcome.

## Verification

```bash
./ci.sh
# gh workflow run platform-maintenance.yml -f job=discovery
```

## PR

Target loop branch.
