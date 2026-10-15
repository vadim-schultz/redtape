---
name: "Chapter 6 — Pipeline drill-down"
overview: "Admin pipeline aggregate API and drill-down page T0–T4 timeline per catalogue service."
todos:
  - id: pipeline-api
    content: "GET /catalogue/{id}/pipeline + pipeline.py stage derivation"
    status: pending
  - id: drilldown-ui
    content: "DiscoveryPipelinePage"
    status: pending
isProject: false
---

# Chapter 6 — Pipeline drill-down

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/discovery-layer-pipeline-drilldown` · **Status:** planned

**Depends on:** [2](02-admin-discovery-api.md), [5](05-crawler-targets-table.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

`GET /api/v1/discovery/admin/catalogue/{id}/pipeline` returns the full staging slice for one service.
`/admin/discovery/pipeline/:id` visualizes stage, tasks, fetches, entities, claims, events.

## Design decisions

**`pipeline.py`** pure functions: given aggregates, compute `T0`–`T4` (unit-tested in API).

**404** when catalogue id unknown.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/pipeline.py` | Stage logic |
| `apps/api/tests/test_discovery_pipeline.py` | Pipeline unit tests |
| `apps/api/tests/test_discovery_admin_pipeline.py` | HTTP tests |
| `apps/web/src/features/discovery-admin/containers/DiscoveryPipelinePage.tsx` | UI |
| `apps/web/src/features/discovery-admin/components/PipelineTimeline.tsx` | Timeline |

## Red tests

| Test | Asserts |
| --- | --- |
| `derive_pipeline_stage · returns T1 when task pending` | Unit happy |
| `derive_pipeline_stage · returns T0 when no tasks` | Unit |
| `GET /catalogue/{id}/pipeline · returns 404 for unknown id` | HTTP negative |
| `GET /catalogue/{id}/pipeline · includes tasks and events for seeded row` | HTTP happy |
| `DiscoveryPipelinePage · shows stage label from API` | Vitest happy |

## Green

1. `pipeline.py` + unit tests 1–2.
2. Admin aggregate endpoint; tests 3–4.
3. Web page; test 5.

## Refactor gate

Stage derivation is a single function with explicit ordered rules, not nested if/elif per stage. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_pipeline.py tests/test_discovery_admin_pipeline.py
cd ../web
npm run test -- src/features/discovery-admin/containers/DiscoveryPipelinePage.test.tsx
cd ../.. && ./ci.sh
```

## Out of scope

Emit preview section (chapter 7).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-pipeline-drilldown
```

```text
test(api): discovery pipeline stage derivation

feat(api): add discovery pipeline aggregate endpoint

test(web): pipeline drill-down page

feat(web): add discovery pipeline drill-down UI
```

Open PR into `feat/plans-discovery-layer`.
