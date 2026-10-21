---
name: "Chapter 3 — Docs canon and ops loop"
overview: "Document v7 tree walk in canon and ops; add chief-of-staff loop pointer."
todos:
  - id: canon
    content: "government-data-sources.md v7 section"
    status: pending
  - id: ops
    content: "discovery-online PVOG 400 triage + loops/pvog-v7-ingest.md"
    status: pending
  - id: skill
    content: "redtape-pvog SKILL pagination + external_id"
    status: pending
isProject: false
---

# Chapter 3 — Docs canon and ops loop

**Repo:** `redtape` (docs) · **Branch:** `docs/pvog-v7-ingest-canon` · **Status:** planned

**Depends on:** [02](02-v7-row-mapping.md) merged · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-pvog-v7-ingest`

---

## Goal

Operators and implementers have one place to read v7 behavior; chief of staff can re-run this suite from `docs/operations/loops/`.

## Files

| Path | Change |
| --- | --- |
| [`docs/discovery/government-data-sources.md`](../../../docs/discovery/government-data-sources.md) | v7 required params; federal tree-walk ingest |
| [`docs/operations/discovery-online.md`](../../../docs/operations/discovery-online.md) | Failure triage: PVOG 400 / 1901 |
| [`docs/operations/loops/pvog-v7-ingest.md`](../../../docs/operations/loops/pvog-v7-ingest.md) | New CoS loop doc (mirror discovery-online-smoke) |
| [`.cursor/skills/redtape-pvog/SKILL.md`](../../../.cursor/skills/redtape-pvog/SKILL.md) | Pagination + mapping |

## TDD loop

Docs-only — run existing runbook tests if discovery-online.md changes trigger them:

```bash
cd apps/api && uv run pytest tests/test_discovery_operations_runbook.py -q
```

## Refactor gate

No production code — report no refactor needed.

## Verification

```bash
./ci.sh
```

Operator (post-release merge): **Actions → Platform maintenance → job `discovery`** green through PVOG and worker drain.

## PR

Target loop branch only.
