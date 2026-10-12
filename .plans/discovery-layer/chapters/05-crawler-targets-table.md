---
name: "Chapter 5 — Crawler targets table"
overview: "Queue table wired to GET admin/discovery/tasks."
todos: []
isProject: false
---

# Chapter 5 — Crawler targets table

**Branch:** `feat/discovery-layer-crawler-queue-ui` · **Status:** planned · **Depends on:** 2,4

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Queue table wired to GET admin/discovery/tasks.

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
