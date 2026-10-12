---
name: "Chapter 1 — Staging migration + lineage"
overview: "Alembic migration for staging tables and discovery_event."
todos: []
isProject: false
---

# Chapter 1 — Staging migration + lineage

**Branch:** `feat/discovery-layer-staging-migration` · **Status:** planned · **Depends on:** none

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Alembic migration for staging tables and discovery_event.

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
