---
name: "Chapter 6 — Pipeline drill-down"
overview: "Catalogue index and per-row T0→emit timeline."
todos: []
isProject: false
---

# Chapter 6 — Pipeline drill-down

**Branch:** `feat/discovery-layer-pipeline-drilldown` · **Status:** planned · **Depends on:** 2,5

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Catalogue index and per-row T0→emit timeline.

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
