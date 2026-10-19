---
name: Discovery online smoke — Gaps and decisions
overview: "Settled decisions for batch-500 triage, federal jurisdiction id canon, and local CI database URL."
isProject: false
---

# Discovery online smoke — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **Triage before code** — chapter 1 confirms root cause (traceback + minimal curl + SQL); chapters 2–4 assume D2 unless disproven. |
| D2 | **`FEDERAL_JURISDICTION_ID` = live `jurisdiction.id` for `kind=COUNTRY`, `code=DE`** — not the seed placeholder when OpenPLZ has run. |
| D3 | **Operator fixes GitHub secret** in chapter 2; no `DATABASE_URL` in discovery GHA job. |
| D4 | **Chapter 3 (API 422)** ships only if triage shows FK `IntegrityError` — improves operability, not required if secret fix alone greens smoke. |
| D5 | **Chapter 4** — API `pytest` in [`ci.sh`](../../ci.sh) must set the same `DATABASE_URL` as [`.github/workflows/api-lint-test.yml`](../../.github/workflows/api-lint-test.yml); ingest pytest stays on explicit local mock list. |
| D6 | **PR CI remains fixture-only** for government APIs ([discovery-online D10](../discovery-online/gaps-and-decisions.md)). |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| Machine `GET /jurisdictions/federal` | Operators want secret-free ingest; needs new route + policy |
| `conftest` remote-URL guard | Contributors keep hitting Supabase despite `ci.sh` fix |
| Render log verbosity | Tracebacks not visible without debug deploy |
