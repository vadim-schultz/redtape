---
name: "Chapter 14 — Catalogue task fanout"
overview: "Rules that enqueue enrich_metadata and secondary fetch tasks after catalogue upsert; visible in pipeline."
todos:
  - id: fanout
    content: "FanoutService invoked after batch upsert"
    status: pending
  - id: events
    content: "task_enqueued events for fanout tasks"
    status: pending
isProject: false
---

# Chapter 14 — Catalogue task fanout

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-layer-task-fanout` · **Status:** planned

**Depends on:** [3](03-task-auto-enqueue-claim.md), [12](12-govdata-ozg-ingest.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

After catalogue ingest, additional `discovery_task` rows are created by policy (e.g. enrich when
`source=govdata` and FIM id present in `raw_payload`) so admin pipeline shows fan-out beyond the initial
`fetch_url` task.

## Design decisions

**Fanout runs inside** `DiscoveryService` after successful batch upsert — not a background job (D4).

**Idempotent:** re-upsert does not duplicate identical pending tasks (match on `kind` + `target_url`).

**Priority:** enrich tasks lower priority (higher number) than fetch.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/fanout.py` | Rules |
| `apps/api/app/features/discovery/service.py` | Hook fanout |
| `apps/api/tests/test_discovery_fanout.py` | Tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `fanout · enqueues enrich_metadata when raw_payload contains fim_id` | Happy path |
| `fanout · does not duplicate pending enrich task on re-upsert` | Happy path idempotent |
| `fanout · skips enrich when fim_id missing` | Negative / no-op |
| `batch upsert integration · creates fetch and enrich tasks` | HTTP happy |

## Green

1. `fanout.py` pure rules; tests 1–3.
2. Service hook + integration test 4.

## Refactor gate

One function per fanout rule; registry list if more than two rules. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_fanout.py
cd ../.. && ./ci.sh
```

## Out of scope

Running enrich CLIs (chapter 17).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-task-fanout
```

```text
test(api): discovery catalogue task fanout rules

feat(api): enqueue fanout discovery tasks after catalogue upsert
```

Open PR into `feat/plans-discovery-layer`.
