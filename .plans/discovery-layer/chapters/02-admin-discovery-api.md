---
name: "Chapter 2 — Admin discovery API"
overview: "Read-only admin lists and pipeline aggregate DTO."
todos: []
isProject: false
---

# Chapter 2 — Admin discovery API

**Branch:** `feat/discovery-layer-admin-api` · **Status:** planned · **Depends on:** 1

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Read-only admin lists and pipeline aggregate DTO.

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
