---
name: "Chapter 2 — Federal jurisdiction id"
overview: "Align FEDERAL_JURISDICTION_ID with production DE row; document OpenPLZ vs seed UUID; optional print script."
todos:
  - id: secret
    content: "Update GitHub FEDERAL_JURISDICTION_ID to SQL id"
    status: pending
  - id: docs
    content: "Fix discovery-online + deployment-checklist + scheduled-jobs canon"
    status: pending
  - id: script
    content: "Optional scripts/print_federal_jurisdiction_id.py"
    status: pending
isProject: false
---

# Chapter 2 — Federal jurisdiction id

**Repo:** `redtape` · **Branch:** `feat/discovery-online-smoke-federal-jurisdiction` · **Status:** planned

**Depends on:** [01](01-triage-batch-500.md) confirms FK / id mismatch · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online-smoke`

---

## Goal

GHA discovery job posts catalogue batches with a `jurisdiction_id` that **exists** in production. Operators can resolve the correct UUID without guessing the seed placeholder.

## Design decisions

**Secret source of truth:** `SELECT id FROM jurisdiction WHERE kind = 'COUNTRY' AND code = 'DE'`.

**OpenPLZ id** (when import ran first): `44107a34-a8d3-53f9-8dc2-da5b133c12bd` — verify on your DB; do not hardcode in secret without SQL check.

**Operator action (required):** Update GitHub repository secret `FEDERAL_JURISDICTION_ID`; re-run minimal curl from chapter 1 → **201**.

## Files

| Path | Change |
| --- | --- |
| [`docs/operations/discovery-online.md`](../../../docs/operations/discovery-online.md) | Secret table: query DE id, not “always seed UUID” |
| [`docs/operations/discovery-online-production-setup.md`](../../../docs/operations/discovery-online-production-setup.md) | Part 3 secrets + §4.4 triage |
| [`docs/operations/deployment-checklist.md`](../../../docs/operations/deployment-checklist.md) | Same canon |
| [`docs/operations/scheduled-jobs.md`](../../../docs/operations/scheduled-jobs.md) | Footnote on OpenPLZ id |
| [`apps/api/scripts/print_federal_jurisdiction_id.py`](../../../apps/api/scripts/print_federal_jurisdiction_id.py) | Optional: print DE country UUID from `DATABASE_URL` |

## TDD loop

| Test | Asserts |
| --- | --- |
| `test_discovery_operations_runbook · federal jurisdiction docs mention DE query` | Doc link / phrase present (if pattern exists) |
| `test_print_federal_jurisdiction_id · prints uuid for seeded DE` | Only if script added — uses `db_session` + seed country row |

## Refactor gate

Docs/script only unless script added — audit new script per project structure rules.

## Verification

```bash
./ci.sh
gh workflow run platform-maintenance.yml -f job=discovery
# Expect: GovData OZG catalogue fetch step green
```

## PR

Target loop branch.
