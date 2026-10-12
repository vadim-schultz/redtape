---
name: "Chapter 23 — Docs sync"
overview: "STATUS.md, .plans/README statuses, and planning cross-links after discovery loop ships."
todos:
  - id: status
    content: "docs/planning/STATUS.md wave row"
    status: pending
  - id: plans-readme
    content: "Mark discovery-layer shipped in rollout"
    status: pending
isProject: false
---

# Chapter 23 — Docs sync

**Repo:** `redtape` (docs) · **Branch:** `docs/discovery-layer-sync` · **Status:** planned

**Depends on:** [22](22-orchestration-runbook.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Planning docs reflect shipped discovery layer; deferred chapters 16/20/21 remain explicitly open.

## Design decisions

Update [STATUS.md](../../../docs/planning/STATUS.md) discovery row to **shipped** with links to
`docs/operations/discovery-layer.md` and feature paths.

[01-rollout.md](../01-rollout.md) chapter table statuses → `shipped` for in-loop chapters; deferred stay
`deferred`.

## Files

| Path | Change |
| --- | --- |
| `docs/planning/STATUS.md` | Discovery wave |
| `.plans/discovery-layer/01-rollout.md` | Status column |
| `.plans/README.md` | Discovery status line |

## Red tests

| Check | Asserts |
| --- | --- |
| STATUS mentions discovery-layer runbook | Link present |
| All relative links in edited files resolve | Link check |
| `docs/discovery/government-data-sources.md` links resolve | Canon included in link check |

## Green

Apply doc edits; verify links.

## Refactor gate

No refactor needed — docs chapter.

## Verification

```bash
./ci.sh
```

## Out of scope

Crawler strand TBD updates (until chapter 20 ships elsewhere).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b docs/discovery-layer-sync
```

```text
docs: record discovery layer suite as shipped
```

Open PR into `feat/plans-discovery-layer`.
