# Discovery admin flow consolidation - rollout

Chapters C1 and C2 run first. The flow data, the flow page, the frontend removal and the backend removal then run in order. The release chapter opens one pull request into `main`.

## Scheduling matrix

| ID | Chapter | Depends on | Batch | Touches |
| --- | --- | --- | ---: | --- |
| C1 | [Flow aggregates](chapters/01-flow-aggregates.md) | none | 1 | `apps/api/app/features/discovery/flow/`, `apps/api/app/features/discovery/admin_service.py`, `apps/api/app/schema/discovery/flow.py`, `apps/api/tests/test_discovery_flow_route.py`, `apps/api/tests/test_discovery_flow_aggregates.py` |
| C2 | [Flag-only language menu](chapters/02-flag-language-menu.md) | none | 1 | `apps/web/src/components/layout/menu/`, `apps/web/src/i18n/fallback/`, `apps/api/scripts/seed_data/translations/` |
| C3 | [Flow translation and failures](chapters/03-flow-translation-and-failures.md) | C1 | 2 | `apps/api/app/features/discovery/flow/`, `apps/api/app/schema/discovery/flow.py`, `apps/api/tests/test_discovery_flow_translation.py`, `apps/api/tests/test_discovery_flow_failures.py` |
| C4 | [Flow page and probe](chapters/04-flow-page-and-probe.md) | C1, C3 | 3 | `apps/web/src/features/discovery-admin/components/FlowView/`, `apps/web/src/features/discovery-admin/containers/DiscoveryFlowPage.tsx`, `apps/web/src/features/discovery-admin/containers/DiscoveryFlowPage.test.tsx`, `apps/web/src/features/discovery-admin/types/flow.ts`, `apps/web/src/features/discovery-admin/utils/`, `apps/web/src/features/discovery-admin/hooks/useDiscoveryAdminProbe.ts`, `apps/web/src/features/discovery-admin/hooks/useDiscoveryAdminProbe.test.tsx`, `apps/web/src/features/discovery-admin/services/discoveryAdminApi.ts`, `apps/web/src/i18n/fallback/` |
| C5 | [Frontend view removal](chapters/05-frontend-view-removal.md) | C4 | 4 | `apps/web/src/features/discovery-admin/`, `apps/web/src/app/`, `apps/web/src/components/layout/`, `apps/web/src/test/adminRoutesApi.ts`, `apps/web/src/i18n/fallback/` |
| C6 | [Backend endpoint removal](chapters/06-backend-endpoint-removal.md) | C3, C5 | 5 | `apps/api/app/features/discovery/`, `apps/api/app/features/translation/`, `apps/api/app/schema/discovery/read.py`, `apps/api/app/schema/translation/admin.py`, `apps/api/app/shared/list_query/`, `apps/api/app/main.py`, `apps/api/tests/` |
| C7 | [Docs and runbook](chapters/07-docs-and-runbook.md) | C6 | 6 | `docs/operations/`, `docs/planning/STATUS.md`, `render.yaml`, `apps/api/tests/test_deployment_checklist.py`, `apps/api/tests/test_discovery_operations_runbook.py` |
| C8 | [Release](chapters/08-release.md) | C1, C2, C3, C4, C5, C6, C7 | 7 | none |

Each batch holds chapters whose `Touches` paths do not overlap. Batch 1 holds C1 and C2. C1 works in the flow package, the admin service and the flow schema. C2 works in the menu folder, the fallback bundles and the seed translations. The two sets share no path. Batches 2 to 7 hold one chapter each. Each of those chapters changes a file that the previous chapter changed, or it deletes what the previous chapter stopped using.

## Parallel batches

- Batch 1: C1, C2. The two chapters share no path. C1 changes only the backend flow code and its tests. C2 changes only the web menu, the fallback bundles and the seed translations.
- Batch 2: C3. It changes the flow package and the flow schema that C1 changed. It starts only after C1 integrates.
- Batch 3: C4. It needs the final flow contract from C1 and C3.
- Batch 4: C5. It deletes files that C4 may still import. It starts only after C4 integrates.
- Batch 5: C6. It removes endpoints only after C5 removes every caller of them.
- Batch 6: C7. The docs describe the final routes, so C7 starts after C6.
- Batch 7: C8. The release chapter runs after every chapter integrates.

C2 may integrate at any time after batch 1. It shares no path with any later chapter, so the chief of staff may place it in any later batch.

## Integration order

1. C1 - Flow aggregates
2. C2 - Flag-only language menu
3. C3 - Flow translation and failures
4. C4 - Flow page and probe
5. C5 - Frontend view removal
6. C6 - Backend endpoint removal
7. C7 - Docs and runbook
8. C8 - Release

## Critical path

C1 -> C3 -> C4 -> C5 -> C6 -> C7 -> C8

C2 is off the critical path. C8 waits for it.

## Per-chapter gate

A chapter passes the gate when all of the following are true:

1. Every red test is committed and fails for the right reason. Each slice has one happy-path test and one negative-path test.
2. The verification commands of the chapter pass on the chapter branch.
3. The local gate passes on the chapter branch, with the loop branch merged in. The gate is `./ci.sh all`. The script takes no arguments, so this command runs every step.
4. The refactor report is filled in. It names each candidate from the chapter, and it states the outcome of each.
5. The chief of staff merges the chapter branch into the loop branch with `--no-ff`, and the local gate passes on the loop branch.

Chapters do not push, and they get no remote CI. The release chapter, C8, runs remote CI once, on the pull request into `main`.

## Final gate

The loop branch must hold these facts before the release pull request opens:

1. Every chapter row in the run ledger shows `done`.
2. No code, test, route, or current doc names a removed admin route. Run this command from the repository root. It must print nothing:

```bash
grep -rIn --exclude-dir=node_modules --exclude-dir=.venv \
  -E "admin/discovery/(catalogue|coverage|tasks|documents|pipeline)|discovery/admin/(tasks|catalogue|coverage|candidates|budgets)|admin/translations" \
  apps docs render.yaml | grep -v "docs/operations/loops/"
```

3. The local gate passes on the loop branch head: `./ci.sh all` exits 0.
4. The flow route answers with every field of the contract in [00-architecture.md](00-architecture.md). Its tests pass.

The release chapter, C8, runs this gate once. The chief of staff executes it, and no implementer does. It runs the local gate on the loop branch head, opens one pull request from the loop branch into `main`, watches the remote checks, and tags the release only after they pass.
