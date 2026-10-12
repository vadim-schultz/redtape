---
name: "Chapter 7 — Emit preview panel"
overview: "GET emit-preview; UI panel without POST suggestions."
todos: []
isProject: false
---

# Chapter 7 — Emit preview panel

**Branch:** `feat/discovery-layer-emit-preview` · **Status:** planned · **Depends on:** 2,6

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

GET emit-preview; UI panel without POST suggestions.

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
