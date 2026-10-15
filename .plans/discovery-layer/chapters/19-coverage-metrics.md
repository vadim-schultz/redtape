---
name: "Chapter 19 — Coverage metrics"
overview: "Admin coverage endpoint and catalogue index chips for ingest completeness by source."
todos:
  - id: api
    content: "GET /discovery/admin/coverage"
    status: pending
  - id: ui
    content: "Summary chips on catalogue index page"
    status: pending
isProject: false
---

# Chapter 19 — Coverage metrics

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/discovery-layer-coverage` · **Status:** planned

**Depends on:** [2](02-admin-discovery-api.md), [14](14-catalogue-task-fanout.md), [15](15-discovery-entity-dedup.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Catalogue index shows chips: counts by `discovery_source`, tasks pending/completed, rows at T3+ stage.

## Design decisions

**Coverage DTO:** `{by_source: {govdata: n, ...}, tasks_pending, tasks_failed, emit_ready_count}`.

**Web:** extend catalogue page from chapter 5 pattern or new `DiscoveryCataloguePage` if not yet built —
add chips component.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/service.py` | Coverage aggregation |
| `apps/api/tests/test_discovery_coverage.py` | API tests |
| `apps/web/src/features/discovery-admin/containers/DiscoveryCataloguePage.tsx` | Index + chips |
| `apps/web/src/features/discovery-admin/components/CoverageChips.tsx` | Chips |

## Red tests

| Test | Asserts |
| --- | --- |
| `GET /coverage · returns counts for seeded mixed sources` | API happy |
| `GET /coverage · returns 403 for non-admin` | API negative |
| `CoverageChips · renders source counts from API` | Vitest happy |

## Green

1. Coverage query; API tests 1–2.
2. Catalogue page + chips; test 3.

## Refactor gate

Coverage SQL in repository method, not controller. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_coverage.py
cd ../web
npm run test -- src/features/discovery-admin/components/CoverageChips.test.tsx
cd ../.. && ./ci.sh
```

## Out of scope

External analytics export.

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-coverage
```

```text
test(api): discovery coverage metrics endpoint

feat(web): discovery catalogue coverage chips
```

Open PR into `feat/plans-discovery-layer`.
