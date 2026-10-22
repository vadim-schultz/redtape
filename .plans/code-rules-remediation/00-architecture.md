---
name: Code rules remediation — Architecture
overview: "Bring the Litestar API and the React web app in line with the house coding rules (Metz size limits, rule of three, layer breakdown, strict types) and align the frontend layout with rsb-test-storage."
isProject: false
---

# Code rules remediation — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/) · **Ledger:** [run-ledger.md](run-ledger.md)

---

## 1. Why

An audit of `apps/api` and `apps/web` (2026-10-22) found the code well layered overall, with concentrated violations of the house rules. A second goal came from the operator: align the frontend feature layout with the sibling repo `rsb-test-storage`. Chapter 0 (green CI) is already done and on `main`.

## 2. The standard

The rules live in `~/.cursor/rules` (`code-structure`, `refactor-step`, `tdd`, `type-hinting`, `docstrings`, `git-workflow`). The implementer may not see that folder, so the working summary is here:

| Rule | Limit |
| --- | --- |
| Function or method | about 5 lines of code |
| Class, module, or file | about 100 lines |
| Parameters (props for React) | more than **3** means a DTO / one object |
| Rule of three | **total** arms for one decision (`if`/`elif`/`match`), pre-existing included. More than 2 means a factory, adapter, or handler per variant |
| Nesting | one level; guard clauses and early returns |
| `match` | dispatch only; arms call named units |
| Boolean flag parameter | two methods in disguise; select the variant at the boundary |
| One-line wrappers | do not extract a trivial delegation |
| Types (Python) | never `Any` or `object` in annotations; `TypedDict`, `Protocol`, discriminated unions |
| Docstrings (Python) | module, public class, method, function, `__init__` (ruff pydocstyle) |
| TDD | each slice has a happy-path **and** a negative-path test, red then green then refactor |
| Refactor gate | audit the whole containing class or function, report the outcome even when "no change" |

For the frontend the same limits apply with React terms: props are the parameters, containers/components/hooks/services are the layers.

## 3. Backend findings (`apps/api/app`)

| # | Finding | Where |
| --- | --- | --- |
| B1 | HTTP concerns in services and repositories. Discovery raises Litestar `NotFoundException`, `ValidationException`, and a repository builds a 422 `ClientException`. Suggestions and voting do it right: domain errors in the service, mapped by the controller (`suggestions/controller.py`, `voting/controller.py`). | `features/discovery/service.py` (about lines 273-386), `emit.py:45`, `repository.py:10,81-84` |
| B2 | `DiscoveryRepository` is about 427 lines and holds business logic: fingerprinting, upsert, rollback, race recovery, DB error-code parsing. | `features/discovery/repository.py` (`append_claim` ~426, `upsert_catalogue_item` ~102) |
| B3 | Guards open their own `SessionLocal` and wire services; three copies. `principal: object` casts in suggestions. Flag checks mixed with the allowlist check. | `auth/guards.py`, `features/discovery/guards.py:99-111`, `suggestions/controller.py:68` |
| B4 | Controllers: `list_documents` and `list_suggestions` take 8 parameters; `suggestions` `create` catches six errors and builds the response; locale lookup copied 5 times; offset/limit `Parameter` pairs copied 4 times. | `documents/controller.py:25`, `suggestions/controller.py:64-97`, `locations/controller.py`, `taxonomy/controller.py` |
| B5 | `DiscoveryAdminService.catalogue_pipeline` mutates `pipeline_stage` during an admin GET. Stage transitions are string literals in three places. | `discovery/service.py` (~170-214, 351), `pipeline.py`, `fanout.py` |
| B6 | Oversized classes and methods. 7 classes over 100 lines; the audit counted 141 of 384 methods over 5 lines (longest 35). Re-measure at the start. | `DocumentService`, `SuggestionService`, `DiscoveryMachineService`, `DiscoveryEmitService`, `OpenPLZClient` |

## 4. Frontend findings (`apps/web/src`)

| # | Finding | Where |
| --- | --- | --- |
| F1 | Props far above 3: `QueryStatusView` takes 11; about 12 `*View` and `*QueryStatus` components take 5-9. Query state is threaded as loose booleans. | `components/feedback/QueryStatusView.tsx`, `features/*/components/*View.tsx`, `*QueryStatus.tsx` |
| F2 | Duplication past three: the QueryStatus wrapper (5 copies), the `count_one`/`count_other` logic (3 copies), refetch/refresh plumbing (about 7 containers). | `DocumentsListQueryStatus`, `SuggestionsListQueryStatus`, `DiscoveryTasksQueryStatus`, `DocumentDetailQueryStatus`, `SuggestionDetailQueryStatus` |
| F3 | Layering: `LocaleContext` does a raw `fetch`; `AuthContext` hard-wires its gateway; components import service error classes; `DocumentFilters` and `EmitPreviewPanel` own queries. | `contexts/LocaleContext.tsx`, `features/auth/contexts/AuthContext.tsx`, `DocumentDetailQueryStatus.tsx`, `SuggestPage.tsx` |
| F4 | Hygiene: stray tracked `LocaleContext.tsx.draft`; `DiscoveryCataloguePage` mixes two queries and state derivation (`queryStateFor`, a non-null assertion). | `contexts/`, `features/discovery-admin/containers/DiscoveryCataloguePage.tsx` |
| F5 | Layout differs from rsb-test-storage (section 5). | all features |

## 5. Target frontend layout (rsb-test-storage)

Reference: `/home/schult_v/projects/rsb-test-storage/frontend/src`.

```
src/
  app/            routes.tsx, queryClient, queryKeys.ts (central key factories)
  components/     shared: ui, feedback, layout, data-display
  hooks/          shared hooks (useApiQuery, useSlowRequest, useLocalesQuery)
  utils/ or services/api.ts   shared fetch helpers
  features/<camelCaseName>/
    containers/   <Thing>Page.tsx   route pages: hooks + one View, loading/error branch
    components/   <Thing>View/{<Thing>View, <Thing>Header, <Thing>Table, index.ts}  presentational, props = data + callbacks
    hooks/        use*.ts           thin wrappers over a service and queryKeys
    services/     *Api.ts           API functions and URL builders
    types/        feature-local types, no logic
    utils/        pure helpers
    registry/     only where a real plug-in point exists
  test/           renderWithProviders, setup
```

Rules inferred from rsb: absolute `@/features/<f>/<layer>/<File>` imports, flow container to components and hooks to services to types and utils, barrels on component folders, co-located `X.test.tsx`.

## 6. Invariants

1. **Behaviour-preserving.** Chapters 1-11 change structure, not features. Existing tests stay green; new tests pin behaviour first.
2. **One chapter, one PR into the loop branch.** Refactor gate reported per chapter.
3. **`./ci.sh` is green** before every push. It was green at the end of chapter 0.
4. **No API contract change.** Response bodies and status codes for existing endpoints stay identical (the mapped domain errors must produce the same status codes).
5. **No new dependency.**
