---
name: "Chapter B4 — Discovery performance"
overview: "advance_stage derives the pipeline stage with an early exit, two EXISTS queries and one two-column claim projection instead of three full list loads on every write."
todos:
  - id: characterize
    content: "Pin advance_stage/derive_stage_for results and count statements per call site"
    status: pending
  - id: cheap-queries
    content: "Add exists and projection queries to the discovery repository"
    status: pending
  - id: rewire
    content: "derive_stage_for and stage_of share one stage-input builder; advance_stage exits early"
    status: pending
isProject: false
---

# Chapter B4 — Discovery performance

**Repo:** `redtape` · **Branch:** `refactor/discovery-performance` · **Status:** planned

**Depends on:** A2 (single emit pipeline) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (L3) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/features/discovery/{stage_sync,pipeline_rows,task_enqueue}.py` (plus the repository additions listed under Files)

**Findings:** L3

## Goal

The machine write path stops loading whole task, fetch-log and claim lists just to count them. Stage results are identical for every input; only the number and weight of SQL statements drops. Behaviour is pinned by tests that did not exist before (`advance_stage` and `derive_stage_for` have no direct test; the only stage tests cover the pure `derive_pipeline_stage` in `tests/test_discovery_pipeline.py`).

## The L3 claim, verified by reading the call sites

`stage_sync.derive_stage_for` (`stage_sync.py:17-28`) calls `repo.list_catalogue_claims`, `repo.list_catalogue_tasks` (a join of tasks and `CatalogueService`) and `repo.list_catalogue_fetch_logs` (a join on tasks), each materialising every row, then uses only `len()` on two of them and `(kind, payload)` of the claims. `advance_stage` (`stage_sync.py:31-36`) calls it, then compares ranks.

Callers of `advance_stage`, which is the only caller of `derive_stage_for`:

| Call site | When it runs | Verdict |
| --- | --- | --- |
| `task_queue.py:47` (`enqueue_for_service`), reached from `service.py:_upsert_item` (`service.py:185-190`) inside `batch_upsert`'s per-item comprehension | **once per batch item that has a `portal_url`**. `enqueue_task_if_needed` returns `.task` of an `EnqueueOutcome` (`task_enqueue.py:25-33`), which is never `None`, so the `if task is not None` guard at `task_queue.py:46` is always true: it also runs when the task already existed. | Real repeated work: 3 list loads times batch size. Classic query-per-row, not a lazy-load N+1. |
| `service.py:195` via `_advance_task_catalogue`, from `append_fetch_log` | once per fetch-log append (plus one `get_catalogue`) | Real. |
| `claim_ingest.py:63` via `_advance`, from `ClaimIngest.append` | once per claim append (plus `get_entity` and `get_catalogue`) | **Worst case:** ingest posts claims one at a time, so appending N claims to one catalogue row loads 1 + 2 + ... + N claim rows including their JSON payloads: O(N squared) rows read. |

So the claim is confirmed, with the correction that it is a repeated full-list load per write rather than a lazy-loading N+1, and that the claim path is quadratic. `pipeline_rows.stage_of` (`pipeline_rows.py:66-76`) is the admin read; it already holds the lists for the response, so it costs nothing extra and stays.

What the stage actually needs (`pipeline.py:derive_pipeline_stage`, lines 37-48): `task_count > 0`, `has_fetch_log`, `claim_count > 0` and whether all emit-eligible claims are resolvable. Resolvability inspects each claim's `kind` and `payload`, so claims cannot be reduced to a pure count; the other two reduce to `EXISTS`.

## Design

1. **Early exit.** `advance_stage` returns immediately when `PipelineStage(catalogue.pipeline_stage)` is already `T4`; stages only move forward, so nothing can change. After the first resolvable claim, every later claim append costs zero stage queries.
2. **Cheap queries** (new methods on the existing mixins of `DiscoveryRepository`, `repository/composite.py`):
   - `catalogue_has_tasks(catalogue_id) -> bool` in `repository/task_listing.py` (`SELECT EXISTS(... DiscoveryTask.catalogue_service_id == id)`; no join to `CatalogueService`).
   - `catalogue_has_fetch_log(catalogue_id) -> bool` in `repository/activity.py` (same join on tasks as `list_catalogue_fetch_logs`, as `EXISTS`).
   - `catalogue_claim_kinds_and_payloads(catalogue_id) -> list[tuple[DiscoveryClaimKind, dict[str, object]]]` in `repository/claims.py`: the same join as `list_catalogue_claims`, selecting only `kind` and `payload`, no ordering.
3. **One stage-input builder.** A pure `stage_input(task_count_positive, has_fetch_log, claim_pairs) -> PipelineStageInput` helper in `pipeline.py` (or `stage_sync.py`) used by both `derive_stage_for` and `pipeline_rows.stage_of`, so the `(c.kind, c.payload)` mapping and the `all_emit_claims_resolvable` call exist once. `PipelineStageInput.task_count` becomes a bool-like need; keep the field as is and pass `1 if exists else 0` only if changing the dataclass would touch `tests/test_discovery_pipeline.py`; otherwise rename to `has_tasks`. Prefer the minimal change: pass `int(exists)`.
4. **Do not change** `enqueue_task_if_needed`'s `| None` return type in this chapter unless a characterisation test shows the `None` branch is reachable; if it is dead, return `DiscoveryTask` and delete the guard at `task_queue.py:46` (state it in the PR). Do not skip `advance_stage` when `created` is false: the stage must still be raised for rows whose earlier derivation was missed, and the early exit already makes the repeat cheap.
5. `fanout.py` and `catalogue_upsert.py` are not touched.

Out of scope: the per-entity `normalize_canonical_url` loop in `repository/entities.py:49-51` (`_find_by_normalized_url`) is another scan-in-Python of the same family as L4; note it in the PR and leave it.

## Files

| File | Change |
| --- | --- |
| `apps/api/app/features/discovery/stage_sync.py` | New `derive_stage_for` and `advance_stage` (early exit, three cheap queries). |
| `apps/api/app/features/discovery/pipeline_rows.py` | `stage_of` uses the shared builder. Another chapter (B3) deletes the four `*_dict` mappers at the top of this file; do not touch those. |
| `apps/api/app/features/discovery/task_enqueue.py`, `task_queue.py` | Only the dead `None` guard, if confirmed. |
| `apps/api/app/features/discovery/pipeline.py` | The shared builder, if placed there. |
| `apps/api/app/features/discovery/repository/{task_listing,activity,claims}.py` | The three new methods (addition to the touches table; no other chapter edits these files). |

## TDD loop

### Red

Characterise on the unchanged code first (all green). New file `tests/test_discovery_stage_sync.py` using `db_session` and the `DiscoveryRepository` fixtures from `tests/test_discovery_repository_characterization.py`:

1. Happy path: `test_derive_stage_for_returns_T0_for_a_bare_catalogue_row`, `..._T1_with_a_task`, `..._T2_with_a_fetch_log`, `..._T3_with_an_unresolvable_claim`, `..._T4_with_only_resolvable_emit_claims`, `test_metadata_only_claims_stay_T3`.
2. `test_advance_stage_raises_but_never_lowers` (a row stored at `T4` with no claims stays `T4`; a row at `T0` with a task becomes `T1`).
3. Negative: `test_derive_stage_for_unknown_catalogue_id_is_T0` (no rows anywhere) and `test_new_document_claim_without_official_url_is_not_resolvable`.
4. Call-site pins through the services: `test_batch_upsert_advances_stage_to_T1_for_item_with_portal_url`, `test_batch_upsert_without_portal_url_stays_T0` (negative), `test_append_fetch_log_advances_to_T2`, `test_append_claim_advances_to_T3_then_T4`.

Then the red performance tests, counting statements with a SQLAlchemy `before_cursor_execute` listener on `app.db.engine`:

5. `test_advance_stage_issues_at_most_three_selects` (fails today only on weight; assert statement texts contain `EXISTS` and that no `SELECT ... FROM discovery_claim` returns `id`/`created_at` columns, i.e. the projection).
6. `test_appending_n_claims_reads_constant_rows_per_append` (append 20 claims to one row, assert the per-append statement count does not grow). Fails today: the claim list grows. This is the O(N squared) pin.
7. `test_advance_stage_issues_no_stage_queries_once_T4`.

### Green

1. Add the three repository methods with their own tests (`test_catalogue_has_tasks_true_and_false`, `test_catalogue_has_fetch_log_true_and_false`, `test_claim_projection_returns_kind_and_payload_only`).
2. Rewrite `derive_stage_for`/`advance_stage`; rewire `stage_of`.
3. Remove the dead guard if the characterisation proved it dead.

### Refactor

Gate: judge by responsibility, not line count. `stage_sync.py` should say "keep the stored stage in step with the evidence"; the SQL stays in the repository, the rule stays in `pipeline.py`. Check there is exactly one place that builds a `PipelineStageInput`; do not add a method for a single use (rule of three counts `derive_stage_for`, `stage_of` and the tests; two production uses justify the shared builder, a third repository method does not need a wrapper); keep one nesting level; no new `Any`; every new public symbol gets an imperative docstring; remove the `D` and `ANN401` baseline entries for the files rewritten. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with the statement counts before and after for the three call sites (the numbers are the headline of this chapter).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_discovery_stage_sync.py tests/test_discovery_pipeline.py tests/test_discovery_repository_characterization.py \
  tests/test_discovery_catalogue_title_stage.py tests/test_discovery_admin_pipeline.py tests/test_discovery_machine_api.py \
  tests/test_discovery_service_errors.py tests/test_discovery_task_queue.py tests/test_discovery_fanout.py
cd ../..
./ci.sh
```

`tests/test_discovery_machine_api.py` and `test_discovery_admin_pipeline.py` are slow; run them in the background.

## Parallel notes

Runs in batch 2 alongside T1 step 2, B2, B3, I1, I2, W3, W4. Do not touch `schema/discovery/*`, `features/discovery/{service,url_normalize,admin_service,read_mappers}.py` or `features/auth/*` (B3: it also edits the top of `pipeline_rows.py`, a disjoint hunk, and the file's module docstring, which becomes stale; whoever merges second updates it), `features/discovery/*_controller.py` (B5, later), `features/suggestions/*` (B2). `service.py:195` (`_advance_task_catalogue`) is only a caller: leave it. A2 has already merged, so `emit*.py` is stable. A docstring-only pass (T1 step 2) over `features/discovery` must not run concurrently with this chapter.
