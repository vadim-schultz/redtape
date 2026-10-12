---
name: "Chapter 4 — Admin shell + email gate"
overview: "/admin/discovery visible only to allowlisted email."
todos: []
isProject: false
---

# Chapter 4 — Admin shell + email gate

**Branch:** `feat/discovery-layer-admin-shell` · **Status:** planned · **Depends on:** none

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

/admin/discovery visible only to allowlisted email.

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
