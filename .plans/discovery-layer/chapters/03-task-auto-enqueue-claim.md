---
name: "Chapter 3 — Task auto-enqueue + claim"
overview: "Machine catalogue upsert auto-creates tasks; POST tasks/claim."
todos: []
isProject: false
---

# Chapter 3 — Task auto-enqueue + claim

**Branch:** `feat/discovery-layer-task-queue` · **Status:** planned · **Depends on:** 1

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Machine catalogue upsert auto-creates tasks; POST tasks/claim.

## Red tests

| Test | Asserts |
| --- | --- |
| Happy path | Primary success outcome |
| Negative path | 403 / 404 / 422 as applicable |

## Verification

```bash
cd apps/api && python -m pytest tests/<chapter>.py  # or web vitest
cd ../.. && ./ci.sh
```

Open PR into `feat/plans-discovery-layer`.
