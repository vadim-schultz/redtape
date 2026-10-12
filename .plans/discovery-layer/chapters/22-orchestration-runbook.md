---
name: "Chapter 22 — Orchestration runbook"
overview: "Operations doc: env vars, manual ingest order, admin smoke, loop branch release checklist."
todos:
  - id: runbook
    content: "docs/operations/discovery-layer.md"
    status: pending
isProject: false
---

# Chapter 22 — Orchestration runbook

**Repo:** `redtape` (docs) · **Branch:** `docs/discovery-layer-orchestration` · **Status:** planned

**Depends on:** [18](18-emit-suggestions.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

An operator can run GovData/PVOG ingest, inspect admin UI, and emit suggestions locally without reading
the plan suite.

## Design decisions

Document: `DISCOVERY_ADMIN_EMAILS`, `DISCOVERY_API_KEY`, `DISCOVERY_API_URL`, issuing API key via
`python -m scripts.issue_api_key`.

**Manual sequence:** migrate → seed jurisdiction if needed → govdata CLI → pvog CLI → enrich → admin review
→ machine emit.

Link to [loops/discovery-layer.md](../../../docs/operations/loops/discovery-layer.md) for CoS, not this runbook.

## Files

| Path | Change |
| --- | --- |
| `docs/operations/discovery-layer.md` | New runbook |

## Red tests

| Check | Asserts |
| --- | --- |
| Runbook contains `DISCOVERY_ADMIN_EMAILS` | Required env documented |
| Runbook links to `/admin/discovery/tasks` | Admin route documented |
| Relative links from runbook resolve | Link check |

## Green

Write `docs/operations/discovery-layer.md` satisfying checks.

## Refactor gate

No refactor needed — docs chapter.

## Verification

```bash
# manual link check or project docs script
./ci.sh
```

## Out of scope

GHA scheduled jobs (D4).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b docs/discovery-layer-orchestration
```

```text
docs: add discovery layer operations runbook
```

Open PR into `feat/plans-discovery-layer`.
