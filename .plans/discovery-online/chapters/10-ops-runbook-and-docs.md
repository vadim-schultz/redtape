---
name: "Chapter 10 — Ops runbook and docs sync"
overview: "Primary ops path is scheduled GHA; safe re-run idempotency documented alongside OpenPLZ."
todos:
  - id: runbook
    content: "discovery-online.md operations runbook"
    status: pending
  - id: sync
    content: "Update discovery-layer.md + scheduled-jobs.md"
    status: pending
  - id: plans-readme
    content: "Mark discovery-online shipped in .plans/README"
    status: pending
isProject: false
---

# Chapter 10 — Ops runbook and docs sync

**Repo:** `redtape` · **Branch:** `docs/discovery-online-runbook` · **Status:** planned

**Depends on:** [1](01-maintenance-workflow-router.md)–[9](09-render-production-config.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

Operators use GitHub Actions for catalogue refetch and drain; laptop CLI remains for debugging. Idempotency and duplicate behavior documented next to [openplz-import.md](../../../docs/operations/openplz-import.md).

## Design decisions

**New runbook:** `docs/operations/discovery-online.md` — dispatch workflow, secrets, what each job does, failure triage, manual emit unchanged.

**Update** [`discovery-layer.md`](../../../docs/operations/discovery-layer.md): scheduled path first, manual second.

**Update** [`scheduled-jobs.md`](../../../docs/operations/scheduled-jobs.md): 6-day calendar table.

**Loop doc:** [`loops/discovery-online.md`](../../../docs/operations/loops/discovery-online.md) — mark CoS complete when release merges.

## Files

| Path | Change |
| --- | --- |
| `docs/operations/discovery-online.md` | New operator runbook |
| `docs/operations/discovery-layer.md` | Scheduled-first |
| `docs/operations/scheduled-jobs.md` | Unified maintenance |
| `docs/operations/loops/discovery-online.md` | Status note |
| `.plans/README.md` | discovery-online status → shipped |

## TDD loop

| Test | Asserts |
| --- | --- |
| `test_discovery_docs_sync · links resolve` | Extend docs sync test if present |
| `test_discovery_operations_runbook · mentions platform-maintenance` | Doc string test |

## Refactor gate

Docs-only. Report outcome.

## Verification

```bash
./ci.sh
```

## PR

Target loop branch; final chapter before release PR to `main`.
