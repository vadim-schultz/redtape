---
name: Chapter C6 - Backend endpoint removal
overview: "The admin API keeps only the flow endpoint, and the code and tests that only the removed endpoints used are deleted."
id: C6
depends_on: [C3, C5]
touches:
  - apps/api/app/features/discovery/
  - apps/api/app/features/translation/
  - apps/api/app/schema/discovery/read.py
  - apps/api/app/schema/translation/admin.py
  - apps/api/app/shared/list_query/
  - apps/api/app/main.py
  - apps/api/tests/
execution: chapter-implementer
isProject: false
---

# C6 - Backend endpoint removal

**Depends on:** C3, C5 · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [01-rollout.md](../01-rollout.md)

## Goal

After C6, `GET /api/v1/discovery/admin/flow` is the only admin read endpoint. Each removed endpoint answers `404`. The code, the schemas, the repository methods, the list specs and the tests that only the removed endpoints used are deleted. The machine router, the public candidate API and the flow route keep their responses.

## Read first

- [00-architecture.md](../00-architecture.md): the removed endpoints in the table of the current surface, and invariants I1, I3 and I5.
- [gaps-and-decisions.md](../gaps-and-decisions.md): D1, D5, D10, D11 and O2.
- [01-rollout.md](../01-rollout.md): the per-chapter gate.

## Coordination scope

**Add:**

- `apps/api/tests/test_discovery_admin_removed_routes.py`: the negative tests of the removed endpoints.

**Edit:**

- `apps/api/app/features/discovery/admin_controller.py`: keeps the flow handler only.
- `apps/api/app/features/discovery/budget_controllers.py`: removes `DiscoveryBudgetAdminController` only. The machine controller stays.
- `apps/api/app/features/discovery/router.py`: the admin router lists the flow controller and the guard only.
- `apps/api/app/features/discovery/admin_service.py`: removes the methods of the removed endpoints. Delete the file when no method remains.
- `apps/api/app/features/translation/router.py`: removes `translation_admin_router`.
- `apps/api/app/main.py`: removes the registration and the import of `translation_admin_router`.
- `apps/api/app/schema/discovery/read.py` and `apps/api/app/schema/translation/admin.py`: remove the models that only the removed endpoints used. Keep every model that the flow imports.
- `apps/api/app/shared/list_query/`: removes a list spec only when no route still uses it.
- The test files named in the work items.

**Delete:**

- `apps/api/app/features/discovery/candidate_admin_controller.py` and `apps/api/app/features/discovery/candidate_admin_service.py`, when no other module imports them.
- `apps/api/app/features/discovery/artifact_admin_controller.py`, when no other module imports it.
- `apps/api/app/features/translation/admin_controller.py` and `apps/api/app/features/translation/router.py`'s admin router, after the coverage builder moves into the flow package. Move the builder first, as work item 2 states.
- Each test file that covers only removed endpoints. Work item 3 names the candidates.

**Do not edit:**

- `apps/api/app/features/discovery/machine_controller.py`, `candidate_machine_controller.py`, `artifact_machine_controller.py` and the other machine controllers. The machine router keeps its routes (D10).
- `apps/api/app/features/discovery/repository/` methods that the flow or a machine route still uses.
- `apps/api/alembic/`: no migration is added (I5).
- `apps/api/tests/test_discovery_flow_route.py`, `test_discovery_flow_aggregates.py`, `test_discovery_flow_translation.py` and `test_discovery_flow_failures.py`: these pin the flow contract and stay green.

## Work items

### Endpoints removed

| Method and path | Remove from |
| --- | --- |
| `GET /api/v1/discovery/admin/tasks` | `admin_controller.py` |
| `GET /api/v1/discovery/admin/catalogue` | `admin_controller.py` |
| `GET /api/v1/discovery/admin/coverage` | `admin_controller.py` |
| `GET /api/v1/discovery/admin/catalogue/{catalogue_id}/pipeline` | `admin_controller.py` |
| `GET /api/v1/discovery/admin/catalogue/{catalogue_id}/emit-preview` | `admin_controller.py`. O2 default. |
| `GET /api/v1/discovery/admin/catalogue/{catalogue_id}/artifacts` | `artifact_admin_controller.py` |
| `GET /api/v1/discovery/admin/candidates/` | `candidate_admin_controller.py` |
| `GET /api/v1/discovery/admin/candidates/{candidate_id}` | `candidate_admin_controller.py` |
| `GET /api/v1/discovery/admin/candidates/{candidate_id}/edges` | `candidate_admin_controller.py` |
| `GET /api/v1/discovery/admin/candidates/{candidate_id}/emit-preview` | `candidate_admin_controller.py`. O2 default. |
| `GET /api/v1/discovery/admin/candidates/{candidate_id}/artifacts` | `artifact_admin_controller.py` |
| `GET /api/v1/discovery/admin/budgets/` | `budget_controllers.py` |
| `GET /api/v1/admin/translations/coverage` | `translation/admin_controller.py` |

The flow endpoint, `GET /api/v1/discovery/admin/flow`, stays. The machine routes and the public candidate routes stay. Check the exact paths with the application's route list before the change. Record the list in the refactor report.

The steps of this chapter follow.

1. **Negative tests of the removed endpoints.**
   - **Red, negative path:** `test_discovery_admin_removed_routes.py` requests each path of the table above with an allowlisted admin session. The test asserts `404`. Before the removal, each request answers `200` or another non-404 status, so the test fails for the right reason.
   - **Red, happy path:** the existing flow tests answer `200` for an allowlisted admin, and they answer `403` for a non-admin user. They stay green during this chapter. Run them before the green step to confirm that the guard still holds.
   - **Green:** remove the handlers and the routers named in the table. The negative tests turn green.
   - **Refactor candidates:** `DiscoveryAdminController` keeps one handler. State whether it stays a controller or moves into the flow module. Keep the `DISCOVERY_ADMIN_GUARDS` guard on the admin router. `DISCOVERY_ERROR_HANDLERS` is shared with the machine router, so it stays unchanged.

2. **Move the translation coverage builder.** C3 reads the translation coverage through the translation feature. Before the route goes, move the builder into `apps/api/app/features/discovery/flow/translation.py`. Its only caller after the move is the flow. Then remove `translation/admin_controller.py`, the admin router, the admin service and the registration in `main.py`.
   - **Red:** the flow translation test of C3 still passes after the move. It is the regression for this step.
   - **Green:** the move and the removal, with no change to the output.
   - **Refactor candidates:** the builder keeps one concern, which is the read. The mapping stays in the flow package.

3. **Test files.** Delete a file when every test in it covers a removed endpoint. Trim a file that also covers a machine, public or flow route. The candidates are:
   - Delete: `apps/api/tests/test_discovery_admin_api.py`, `test_discovery_admin_list_query.py`, `test_discovery_admin_pipeline.py`, `test_discovery_candidates_admin_api.py`, `test_discovery_candidates_list_contract.py`, `test_discovery_coverage.py`, `test_translation_admin_api.py`.
   - Decide per file: `test_discovery_artifacts_api.py`, `test_discovery_budgets_api.py`, `test_discovery_emit_preview.py`, `test_discovery_candidate_emit.py`, `test_discovery_list_params.py`, `test_discovery_list_params_openapi.py`, `test_auth_request_resolution.py`, `test_candidates_public_api.py`.
   - Update imports only: `apps/api/tests/conftest.py`, `candidates_public_world.py`, `completeness_world.py`, `fair_selection_support.py` and `search_support.py`, where they import removed fixtures.
   - State each decision in the refactor report.

4. **Repository, schema and list specs.** For each symbol in a removed endpoint, search with `grep`. Delete the symbol when nothing else imports it. Keep a symbol that the flow or a machine route uses. Two examples are `fetch_coverage_metrics` and the summary models of the flow. Keep `shared/list_query/` when another route uses it.
   - **Refactor candidates:** each deleted function leaves no empty helper. No wrapper stays where its callee has one caller.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Flow endpoint | `test_discovery_flow_route.py` answers `200` with the contract | A non-admin user gets `403` from the flow endpoint. The existing guard test checks this. |
| Removed endpoints | `test_discovery_flow_route.py` still answers `200` after the removal | `test_discovery_admin_removed_routes.py` asserts `404` for every path in the table |
| Machine and public routes | The machine and public tests pass without assertion changes | The same tests fail if a machine or public response changes, which is the regression gate for I3 |

## Review gate

- Each removed route test was red before the removal and green after it.
- The machine and public test files pass with no change to their assertions.
- No symbol of a removed endpoint remains, except where the grep in Verification shows an allowed use.
- No migration file was added or changed.
- `apps/api/app/features/discovery/admin_service.py` is deleted, or it holds only symbols that the flow uses. The refactor report says which.

## Out of scope

- The frontend. C5 removed its callers.
- The docs and the runbook. C7 owns them.
- The emit write path under the machine router (O2).

## Verification

```bash
# Run from the repository root. Postgres must answer on 127.0.0.1:5432, as ci.sh expects.
cd apps/api
PYTHONPATH=. DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape_pytest" REQUIRE_DB=1 \
  uv run pytest tests/test_discovery_admin_removed_routes.py tests/test_discovery_flow_route.py \
  tests/test_discovery_flow_aggregates.py tests/test_discovery_flow_translation.py tests/test_discovery_flow_failures.py \
  tests/test_discovery_machine_api.py tests/test_candidates_public_api.py -q
PYTHONPATH=. DATABASE_URL="sqlite:///test.db" uv run ruff check . && uv run ruff format --check . && uv run mypy app scripts
cd ../..
grep -rIn --exclude-dir=.venv -E "list_tasks|list_catalogue|CatalogueListResponse|TASK_LIST_SPEC|CATALOGUE_LIST_SPEC|DiscoveryCandidateAdminController|DiscoveryArtifactAdminController|DiscoveryBudgetAdminController|translation_admin_router|TranslationAdminController" apps/api/app apps/api/tests || echo "no matches"
```

Expected: `pytest` exits 0. `ruff`, `mypy` exit 0. The `grep` prints no match, and the script prints `no matches`.

## Refactor report

_Pending. The implementer fills this in after the refactor pass. It must list each removed route, each deleted file, each trimmed test file and the choice made for `admin_controller.py` and `admin_service.py`._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`.
- Create the chapter branch with `git checkout -b feat/discovery-admin-flow-c6-backend-removal`.
- Commit the red tests first, as `test(discovery-admin): ...`. Then commit the move of the translation builder, as `refactor(discovery-flow): ...`. Then commit the removal, as `refactor(discovery-admin): remove admin endpoints except flow`.
- Run the local gate on the chapter branch with `./ci.sh all`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
