---
name: "Chapter 1 — Triage batch 500"
overview: "Confirm Render traceback, minimal machine batch curl, and DE jurisdiction SQL before any code change."
todos:
  - id: traceback
    content: "Render logs: Python traceback for POST catalogue/batch"
    status: pending
  - id: curl
    content: "Minimal batch curl against DISCOVERY_API_URL"
    status: pending
  - id: sql
    content: "SELECT jurisdiction id for DE country"
    status: pending
isProject: false
---

# Chapter 1 — Triage batch 500

**Repo:** `redtape` · **Branch:** `docs/discovery-online-smoke-triage` · **Status:** planned

**Depends on:** none · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online-smoke`

---

## Goal

Record the **root cause** of Render `500` on `POST /api/v1/discovery/machine/catalogue/batch` during GHA GovData fetch. Outcome is a short triage note (ledger or ops doc) and a go/no-go for chapters 2–3.

## Operator steps

1. **Render** — Same window as failed GHA step; find Python traceback above uvicorn access line.
2. **Minimal curl** — One-item batch (use GitHub secrets locally; do not log `DISCOVERY_API_KEY`):

```bash
curl -sS -w "\nHTTP %{http_code}\n" -X POST "$DISCOVERY_API_URL/api/v1/discovery/machine/catalogue/batch" \
  -H "Content-Type: application/json" -H "X-API-Key: $DISCOVERY_API_KEY" \
  -d "{\"items\":[{\"source\":\"govdata\",\"external_id\":\"smoke:govdata:triage\",\"jurisdiction_id\":\"$FEDERAL_JURISDICTION_ID\",\"title_i18n\":{\"de\":\"Smoke\"},\"portal_url\":\"https://example.gov/test\",\"raw_payload\":{\"id\":\"test\"}}]}"
```

| HTTP | Meaning |
| --- | --- |
| 201 | Secret jurisdiction likely OK; investigate live GovData payload if GHA still fails |
| 500 on minimal body | Config/DB (FK, missing table, unhandled DB error) |
| 401/403/503 | Keys or `DISCOVERY_ADMIN_EMAILS` — not this suite’s primary bug |

3. **SQL** (production `DATABASE_URL`, read-only):

```sql
SELECT id, kind, code FROM jurisdiction WHERE kind = 'COUNTRY' AND code = 'DE';
```

Compare `id` to GitHub secret `FEDERAL_JURISDICTION_ID`.

4. **Migrations** — `alembic current` at head; `catalogue_service` exists.

## Files (optional doc PR)

| Path | Change |
| --- | --- |
| [`docs/operations/discovery-online.md`](../../../docs/operations/discovery-online.md) | Failure triage row: batch 500 + jurisdiction SQL |
| [`docs/operations/discovery-online-production-setup.md`](../../../docs/operations/discovery-online-production-setup.md) | §4.4 table entry |

## TDD loop

Ops chapter — no production code tests. If adding doc tests, follow existing runbook test patterns in `apps/api/tests/test_discovery_operations_runbook.py`.

## Verification

- Triage note in [run-ledger.md](../run-ledger.md) **blocker** column for chapter 02.
- No `./ci.sh` required unless doc PR touches tested markdown.

## PR

Target loop branch; may be **docs-only** or **ledger-only** commit on loop branch.
