---
name: "Chapter 9 — Render production config"
overview: "Document Render env for discovery admin; GHA key rotation; deployment checklist."
todos:
  - id: checklist
    content: "deployment-checklist.md discovery section"
    status: completed
  - id: render
    content: "render.yaml comments for DISCOVERY_*"
    status: completed
isProject: false
---

# Chapter 9 — Render production config

**Repo:** `redtape` · **Branch:** `feat/discovery-online-render-config` · **Status:** shipped (local)

**Depends on:** [2](02-secrets-and-env-canon.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

Production Render service has discovery enabled for admin review (`DISCOVERY_ADMIN_EMAILS`), machine routes accept the GHA API key, and operators have a checklist to verify end-to-end without a laptop.

## Design decisions

**`DISCOVERY_MACHINE_OPT_IN`:** `false` in production when allowlist is set.

**Secrets live in Render dashboard** — not committed in `render.yaml`.

**Key rotation:** issue new `discovery-scheduled-gha` key, update GHA secret, revoke old.

## Files

| Path | Change |
| --- | --- |
| `docs/operations/deployment-checklist.md` | Discovery + GHA secrets |
| `render.yaml` | Comment block for optional `DISCOVERY_ADMIN_EMAILS` |
| `apps/api/.env.example` | Already has discovery vars — cross-link |

## TDD loop

| Test | Asserts |
| --- | --- |
| `test_deployment_checklist · mentions DISCOVERY_ADMIN_EMAILS` | Doc test (add if pattern exists) |
| `test_config_discovery · discovery_enabled when allowlist set` | Existing config tests stay green |

## Refactor gate

Docs-only. Report outcome.

## Verification

```bash
./ci.sh
# Manual: verify admin /admin/discovery after Render env set
```

## PR

Target loop branch.
