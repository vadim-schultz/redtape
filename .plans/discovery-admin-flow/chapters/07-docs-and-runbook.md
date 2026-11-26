---
name: Chapter C7 - Docs and runbook
overview: "The operator docs and the runbook describe the flow-only admin surface, and their tests check the new routes."
id: C7
depends_on: [C6]
touches:
  - docs/operations/
  - docs/planning/STATUS.md
  - render.yaml
  - apps/api/tests/test_deployment_checklist.py
  - apps/api/tests/test_discovery_operations_runbook.py
execution: chapter-implementer
isProject: false
---

# C7 - Docs and runbook

**Depends on:** C6 · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [01-rollout.md](../01-rollout.md)

## Goal

After C7, the operator docs name only the routes that exist. The runbook and the deployment checklist point operators to the flow page and the flow endpoint. The two docs tests check the new routes, and they fail when a removed route returns to the docs.

## Read first

- [00-architecture.md](../00-architecture.md): the current surface, and invariant I8.
- [gaps-and-decisions.md](../gaps-and-decisions.md): D1, D13 and O2.
- [01-rollout.md](../01-rollout.md): the per-chapter gate.

## Coordination scope

**Add:**

- None.

**Edit:**

- `apps/api/tests/test_discovery_operations_runbook.py`: the runbook tests name the flow route and the flow-only menu.
- `apps/api/tests/test_deployment_checklist.py`: the checklist tests name the flow route.
- `docs/operations/discovery-layer.md`: the web admin route surface becomes flow-only. Its anchor `#web-admin-route-surface` keeps its name, because other docs link to it.
- `docs/operations/deployment-checklist.md`: the checks of the admin pages and endpoints name the flow page and the flow endpoint.
- `docs/operations/discovery-online-production-setup.md`: the production verification lists the flow page only.
- `docs/operations/translation-engines.md`: the translation coverage check moves to the flow page.
- `docs/operations/candidate-view.md`, `docs/operations/crawlers-operator-checklist.md`, `docs/operations/discovery-online.md` and `docs/operations/extraction-operator-checklist.md`: each mention of a removed route changes to the flow page or the flow endpoint.
- `docs/planning/STATUS.md`: the discovery row names the flow page, not the removed review UI.
- `docs/operations/admin-tables.md`: see work item 3.

**Delete:**

- `docs/operations/admin-tables.md`, when no section of it describes a route that remains. Remove each link to it. Grep for the file name first.

**Do not edit:**

- `docs/operations/loops/` (D13). Change a file there only when the link check reports a broken link.
- `.plans/`: the plan folders are history.
- `render.yaml`: change it only when its comment names a removed route. Its comment names the `/admin/discovery/*` mount, which remains, so no change is expected.

## Work items

1. **Runbook tests.**
   - **Red, happy path:** `test_runbook_documents_flow_route` asserts that the runbook text names `/admin/discovery/flow`. It replaces `test_runbook_documents_admin_tasks_route`.
   - **Red, happy path:** `test_runbook_documents_complete_admin_route_surface_and_menu_behavior` lists `/admin/discovery`, `/admin/discovery/flow` and `/api/v1/discovery/admin/flow`. The menu labels are `Home`, `Browse Documents`, `Suggest` and `Flow`.
   - **Red, negative path:** `test_runbook_names_no_removed_admin_route` asserts that the runbook text names none of the removed routes. The list holds `/admin/discovery/catalogue`, `/admin/discovery/coverage`, `/admin/discovery/tasks`, `/admin/discovery/documents`, `/admin/discovery/pipeline`, `/api/v1/discovery/admin/tasks`, `/api/v1/discovery/admin/coverage`, `/api/v1/discovery/admin/catalogue` and `/api/v1/admin/translations/coverage`.
   - **Green:** edit the runbook so that each test passes.
   - **Refactor candidates:** the three route lists in the tests share one constant of removed paths. The constant stays at module level in the test file.

2. **Deployment checklist tests.**
   - **Red, happy path:** `test_production_setup_lists_flow_route` replaces `test_production_setup_lists_coverage_route`. It asserts `/admin/discovery/flow` in the production setup doc.
   - **Red, happy path:** the ordered-marker test of the checklist expects the flow endpoint in place of the tasks, coverage and catalogue endpoints. The positions stay sorted.
   - **Red, negative path:** a new test asserts that the checklist names none of the removed endpoints.
   - **Green:** edit the two docs so that the tests pass.
   - **Refactor candidates:** the marker tuples in the test become one tuple of flow markers. No helper wraps a single `read_text` call.

3. **Docs prose.**
   - Rewrite each changed section in the style of the `technical-writing` skill. Use short sentences, active voice and imperative steps. Name a figure by the flow field or the page section that shows it.
   - `docs/operations/admin-tables.md` describes the list contract of the removed lists. Delete the file when nothing in it describes a route that remains. If one section still describes a kept surface, keep that section and rename the file to match.
   - Run the link check after each change. A link to a deleted file fails the check.

4. **Operator checks.** Each check that named a removed page now names the flow page. A check that needs a figure from a removed view now names the flow field that carries it. Keep the order of the steps.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Runbook route surface | `test_runbook_documents_flow_route` | `test_runbook_names_no_removed_admin_route` |
| Deployment checklist | `test_production_setup_lists_flow_route` | The new checklist test that names no removed endpoint |
| Drift check | `scripts/tests/test_docs_drift.py` exits 0 | The drift check reports a retired pattern, when one remains |

## Review gate

- Each docs test was red before its docs change.
- `python3 scripts/tests/test_docs_drift.py` exits 0.
- The link check of `docs/operations/` reports no broken link.
- No file under `docs/operations/loops/` changed, unless the link check named it.
- `docs/operations/admin-tables.md` is deleted or renamed, and no link names a removed file.

## Out of scope

- The loop records under `docs/operations/loops/` (D13).
- Plan folders under `.plans/`.
- The release notes and the release tag. C8 owns them.

## Verification

```bash
# Run from the repository root. Postgres is not needed for these two files.
cd apps/api
PYTHONPATH=. DATABASE_URL="sqlite:///test.db" uv run pytest tests/test_deployment_checklist.py tests/test_discovery_operations_runbook.py -q
cd ../..
python3 scripts/tests/test_docs_drift.py
grep -rIn -E "admin/discovery/(catalogue|coverage|tasks|documents|pipeline)|discovery/admin/(tasks|catalogue|coverage|candidates|budgets)|admin/translations" docs render.yaml | grep -v "docs/operations/loops/" || echo "no matches"
```

Expected: `pytest` exits 0. The drift check exits 0. The `grep` prints no match, and the script prints `no matches`.

## Refactor report

_Pending. The implementer fills this in after the refactor pass. It must list each changed doc, the decision on `admin-tables.md` and the result of the link check._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`.
- Create the chapter branch with `git checkout -b feat/discovery-admin-flow-c7-docs`.
- Commit the red tests first, as `test(docs): ...`. Then commit the docs change, as `docs(discovery-admin): describe the flow-only admin surface`.
- Run the local gate on the chapter branch with `./ci.sh all`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
