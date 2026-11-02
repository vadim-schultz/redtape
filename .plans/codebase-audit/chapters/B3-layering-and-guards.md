---
name: "Chapter B3 — Layering and guards"
overview: "Schema stops importing ORM rows and features; DocumentService loses its promotion half to DocumentPromotion behind a narrow port; auth resolves a principal once per request without a mutable global; typed pipeline rows and JwtClaims replace dict[str, ...]."
todos:
  - id: characterize
    content: "Pin guard, dependency and pipeline-response behaviour; count verifications per request"
    status: pending
  - id: schema-layering
    content: "Move from_row mappers out of schema/discovery; drop the pick_title and validate_url imports"
    status: pending
  - id: typed-rows
    content: "PipelineEntityRow, FetchLogRow, ClaimRow, EventRow replace list[dict[str, object]]"
    status: pending
  - id: document-promotion
    content: "Extract DocumentPromotion from DocumentService and give the suggestion handlers a narrow port"
    status: pending
  - id: auth-once
    content: "Resolve the principal once per request; replace global _jwt_verifier; JwtClaims model"
    status: pending
  - id: hidden-deps
    content: "Inject DiscoveryMachineService collaborators (L11)"
    status: pending
isProject: false
---

# Chapter B3 — Layering and guards

**Repo:** `redtape` · **Branch:** `refactor/layering-and-guards` · **Status:** planned

**Depends on:** A2 (single emit pipeline), B1 (locale and i18n) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (L5, L6, L7, L11, section 5 rows `read.py` and `jwt.py`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/schema/discovery`, `api/features/{documents,auth}`, `api/features/discovery/{service,url_normalize}.py` (plus the additions listed under Parallel notes)

**Findings:** L5, L6, L7, L11, T5 (pipeline rows, `JwtClaims`)

## Goal

Lower layers no longer import upper ones (`schema` does not import features or ORM row classes). `DocumentService` is describable without "and": reads. Promotion writes live in `DocumentPromotion`, which the suggestion handlers reach through a narrow port. A request authenticates once and its identity is reused. No `global` statement remains in `auth/`. The admin pipeline response is fully typed. Wire formats are unchanged except one stated, equivalent datetime spelling.

## Verified facts

### L7 (double guard session): partly wrong, measured

Evidence in code, not from the audit:

- Guards run before dependency injection in Litestar, so a guard cannot receive the request `Session`. `features/auth/guard_session.py:25-31` therefore opens its own `SessionLocal()` per guard call (commit on success, always close).
- **Confirmed double work, machine routes only.** `require_machine` (`guards.py:27-32`) verifies the API key in the guard session (`verify_guard_machine`, `guard_session.py:42-46`), including a hash lookup and `touch_last_used`. Three handlers also declare `machine_principal: MachinePrincipal` (`machine_controller.py:80,166`, `candidate_machine_controller.py:96`), which runs `provide_machine_principal` (`dependencies.py:95-96` -> `machine_principal_from_connection`) a second time in the request session. These are the claim, catalogue emit and candidate emit endpoints (claim is the ingest worker's hot path).
- **Not double, contrary to the audit.** Discovery admin routes use only `require_discovery_admin_allowlist` -> `read_guard_user` (`discovery/guards.py:35-40`): one JWT verification and one user upsert, in the guard session. No discovery handler takes `current_user`. `GET /me`, voting and suggestions use only the dependencies (`current_user`, `optional_user`, `principal`), no guard. `require_role` (`guards.py:16-24`) is referenced only by `tests/test_role_guards.py`, never by a production route.
- Every guarded request still opens two sessions (guard + the `session` dependency when the handler needs one). That is a Litestar ordering constraint. Handing the guard's session to `provide_session` was considered and rejected: it changes commit and rollback semantics in `app/db.py`, outside this chapter. Record it as an optional follow-up.
- `dependencies.py:20` declares `_jwt_verifier: JwtVerifier | None = None` and `:40` `global _jwt_verifier` in `provide_jwt_verifier`, lazily built, with no lock. `guard_session.py:38` calls `provide_jwt_verifier()` directly, so tests patch the module global in nine files (`test_me_endpoint`, `test_vote_endpoints`, `test_suggestions_submit`, `test_role_guards`, `test_suggestion_requirement_kind`, `test_suggestions_read`, `test_suggestions_machine_submit`, `test_discovery_admin_api`, `test_discovery_coverage`).

If the first characterisation test (below) shows a different count, trust the test and edit this section.

### Other claims

| Claim | Check |
| --- | --- |
| L5: `schema/discovery/read.py` imports ORM models | Yes: ORM row classes `CatalogueService`, `DiscoveryArtifact`, `DiscoveryCandidateMention`, `DiscoveryDocumentCandidate`, `DiscoveryTask` (`read.py:10-21`) are used only by the four `from_row` classmethods at lines 47, 91, 248, 306. The enums imported alongside (`DiscoverySource`, `DiscoveryTaskKind`, ...) are real field types and **stay** (they live in `app.models.discovery`; moving them is out of scope). `schema/discovery/artifacts.py:12` has the same pattern (`from_row` at 43 and 56). |
| L5: `candidates.py:10` imports `features.suggestions.slugs.pick_title` | Yes, used once, `candidates.py:42`, only for truthiness. `pick_title(x)` is falsy exactly when every value is blank, so `any(v.strip() for v in self.title_i18n.values())` is equivalent and needs no import. |
| L5: `url_normalize.py` imports `schema.suggestion.payload` | Yes (`url_normalize.py:5`) for `validate_url`. `app/url_normalization.py` already holds `normalize_url`; move `validate_url` and `MAX_URL_LENGTH` there and re-import in `schema/suggestion/payload.py` so `create.py:10` keeps working. |
| L6: `DocumentService` is 223 lines | Responsibilities: reads (`list_documents`, `available_leaf_codes`, `get_document_detail`, `document_ids_in_scope`, `_effective_jurisdiction_id`, `_leaf_codes_in_scope`) versus promotion writes and lookups for suggestions (`create_from_suggestion` + `_resolve_tags/_scores/_leaf_codes/_build_document`, `create_requirement_from_suggestion`, `find_conflicts`, `get_document_jurisdiction`, `requirement_exists`, `requires_directly`, `resolve_jurisdiction_id`). Magic string `source="community"` at `service.py:158` (the column is `String(50)` with default `'canonical'`, `models/document.py:76`). |
| L11: `DiscoveryMachineService.__init__` builds collaborators | `service.py:96-101`: `CatalogueUpsertService`, `TaskQueue`, `ClaimIngest`. Built from a `DiscoveryRepository` in `dependencies.py:46-47`; one test constructs it (`tests/test_discovery_service_errors.py:39`). |
| T5: pipeline rows | `read.py:225-228` are `list[dict[str, object]]`; produced by `pipeline_rows.py:18-63` (`fetch_log_dict`, `entity_dict`, `claim_dict`, `event_dict`) and assembled in `admin_service.py:112-127`. |

## Design

1. **Read mappers.** New `features/discovery/read_mappers.py` with plain functions `task_read`, `catalogue_read`, `candidate_read`, `mention_read`, `artifact_read`, `artifact_summary_read`, replacing the `from_row` classmethods. Callers to update: `admin_service.py:68,75,119,121`, `candidate_admin_service.py:89,92`, `candidate_list_items.py:18`, `artifact_machine_controller.py:56`, `artifact_read.py:64,103`. Delete the ORM imports from `schema/discovery/read.py` and `artifacts.py`. `schema/suggestion/read.py:65` has the same shape but belongs to B2's area; leave it and note it.
2. **Typed pipeline rows.** In `schema/discovery/read.py`: `PipelineEntityRow`, `FetchLogRow`, `ClaimRow`, `EventRow` (frozen Pydantic models; `id: UUID`, timestamps as `datetime`, `kind` as `DiscoveryClaimKind`, `event_type` as `DiscoveryEventType`, `payload` as `JsonObject = dict[str, JsonValue]` from `pydantic`, `confidence: float | None`). Mappers go into `read_mappers.py`; the four `*_dict` functions in `pipeline_rows.py` are deleted. **One wire difference:** `datetime.isoformat()` printed `+00:00`, Pydantic prints `Z` (as every other timestamp in this API already does, for example `DiscoveryTaskRead.created_at`). Pin the old strings in the characterisation test, change the assertion deliberately, and call it out in the PR. The web already parses `Z` (`DiscoveryPipelinePage.test.tsx:117`).
3. **Promotion split.** New `features/documents/promotion.py`: `DocumentPromotion(repository, taxonomy)` with `create_document` (was `create_from_suggestion`), `create_requirement` (was `create_requirement_from_suggestion`), `find_conflicts`, `jurisdiction_of_document`, `existing_requirement`, `requires_directly`, `resolve_jurisdiction_id`, plus a `Protocol` `PromotionPort` listing exactly the methods the suggestion feature calls (handlers: `handlers.py:100,108,130,138,145,162,178,182`; service: `service.py:202`). `resolve_jurisdiction_id` is rewritten without `DocumentFilters` but with identical outcomes (municipality code wins; a raw id must exist). `source="community"` becomes a module constant `COMMUNITY_SOURCE`. `DocumentService` keeps only reads. The three thin delegations (`jurisdiction_of_document`, `existing_requirement`, `requires_directly`) stay as methods because they now *define* the port that keeps the handlers off the repository; document that in their docstrings. `_conflicting_document_ids` and `_same_url` move with `find_conflicts` (B7 later replaces the O(n) scan, L4).
4. **Auth once.**
   - `default_jwt_verifier()` in `auth/dependencies.py`, decorated `@functools.lru_cache(maxsize=1)`, replaces `_jwt_verifier`/`global`. `provide_jwt_verifier` and `guard_session.py:38` call it. Add one test helper `use_jwt_verifier(monkeypatch, verifier)` (in `tests/auth_support.py`) and migrate the nine test files above to it.
   - `JwtClaims` (Pydantic, in `auth/jwt.py`) replaces `TokenClaims` and `_build_claims`: `sub: str`, `email: str` (non-blank), `user_metadata: UserMetadata | None` with `full_name: str | None` (non-string ignored), `display_name` property. `JwtVerifier.verify` returns `JwtClaims.model_validate(payload)`; a missing or blank `email` still raises `AuthError("missing_claim")`; any other validation error raises `AuthError("malformed")`. `UserService.resolve` (`service.py:34`) takes `JwtClaims`. **Defect fix to state in the PR:** today `user_metadata: null` makes `_build_claims` call `.get` on `None` (500); it becomes "no display name". Red first.
   - Resolve once: when a guard authenticates, it records the plain identity in `connection.state` (`auth_api_key_id` or `auth_user_id`, a `UUID`, never an ORM object, because the guard session expires its instances on commit). `provide_machine_principal` and `provide_current_user` then load the row by primary key in the request session instead of verifying again. No cached identity (routes without a guard): behave as today.
5. **Hidden dependencies (L11, discovery half).** `DiscoveryMachineService.__init__` takes `repository, catalogue_upserts, queue, claim_ingest`; `provide_discovery_machine_service` builds them. Update `tests/test_discovery_service_errors.py:39`. The `SuggestionService` half (it builds its handlers and transitions) is done as the last step, after B2 has merged: `provide_suggestion_service` builds `build_kind_handlers`/`SuggestionTransitions` and injects them; its test fixtures (seven modules construct `SuggestionService(...)`) are updated in the same commit.

## Files

| Area | Files |
| --- | --- |
| Schema | `schema/discovery/read.py`, `schema/discovery/artifacts.py`, `schema/discovery/candidates.py`, `schema/suggestion/payload.py` (re-import only), `app/url_normalization.py` |
| Discovery | New `features/discovery/read_mappers.py`; `admin_service.py`, `candidate_admin_service.py`, `candidate_list_items.py`, `artifact_machine_controller.py`, `artifact_read.py` (call sites); `pipeline_rows.py` (delete the four dict mappers); `url_normalize.py` (import); `service.py`, `dependencies.py` (L11) |
| Documents | New `features/documents/promotion.py`; `service.py` (reads only); `dependencies.py` (provide both) |
| Auth | `auth/jwt.py`, `auth/service.py:9,34`, `auth/dependencies.py`, `auth/guard_session.py`, `auth/guards.py` (record identity), `discovery/guards.py:35-40` (uses the same cache) |
| Suggestions (last step, after B2) | `suggestions/handlers.py`, `suggestions/service.py`, `suggestions/dependencies.py`: retype `DocumentService` to `PromotionPort`; inject handlers (L11) |
| Tests | `tests/auth_support.py` (new) and the nine monkeypatch sites; `test_jwt_verifier.py:11,83`, `test_current_user.py:11,121` (`JwtClaims`); the eight modules that build `DocumentService(...)` for the suggestion service (`test_vote_service`, `test_suggestion_duplicates`, `test_suggestion_transitions`, `test_suggestion_service`, `test_promote_new_document`, `test_promote_requirement_edge`, `test_discovery_candidate_emit`, `test_document_service`) switch to `DocumentPromotion` where the suggestion service is built |

## TDD loop

### Red

Characterise on the unchanged code first (all green):

1. `tests/test_auth_request_resolution.py` (new): `test_machine_claim_verifies_the_api_key_twice_today` (count `ApiKeyService.verify` calls with a spy on the endpoint at `machine_controller.py:80`), `test_admin_route_verifies_the_jwt_once`, `test_me_endpoint_verifies_the_jwt_once`. These document the facts above; the first is expected to flip to "once".
2. Pipeline: extend `tests/test_discovery_admin_pipeline.py` with `test_pipeline_response_pins_fetch_log_entity_claim_event_keys_and_values` (exact key sets and the `+00:00` strings), plus a negative `test_pipeline_for_catalogue_without_rows_returns_empty_lists`.
3. Layering: `test_schema_discovery_imports_no_feature_and_no_orm_row_class` (AST scan of `schema/discovery/*.py`: no `app.features` import; from `app.models` only names that are `Enum` subclasses). Fails now.
4. Documents: `test_resolve_jurisdiction_id_by_municipality_code_by_id_and_unknown` (three arms incl. negative: unknown id returns `None`), `test_find_conflicts_matches_slug_or_normalized_url` (exists as `tests/test_document_conflicts.py`, keep).
5. JWT: `test_user_metadata_null_is_accepted_without_display_name` (red: 500/AttributeError today), `test_blank_email_raises_missing_claim`, `test_non_string_full_name_is_ignored`, `test_malformed_claims_raise_malformed`.

Then new-behaviour red tests:

6. `test_default_jwt_verifier_is_cached_and_patchable` and `test_auth_module_has_no_global_statement` (source scan).
7. `test_machine_claim_verifies_the_api_key_once` (flips test 1), `test_cached_identity_is_not_trusted_across_requests` (two requests with different keys each verify once; negative: revoked key still 401 on the second request).
8. `test_document_service_has_no_promotion_methods`, `test_promotion_port_covers_every_call_the_handlers_make` (type-level: `mypy` is the check; add a runtime `isinstance` against a `runtime_checkable` Protocol).
9. `test_discovery_machine_service_receives_its_collaborators`.

### Green

Order, each step green before the next: (1) `validate_url` move, `pick_title` removal from `candidates.py`; (2) read mappers and typed rows; (3) `JwtClaims`, lru_cache verifier, test helper; (4) identity recorded and reused; (5) `DocumentPromotion` and the port, tests rewired; (6) L11 discovery half; (7) suggestions retype and L11 suggestions half **only after B2 is merged into the loop branch**.

### Refactor

Gate: judge by responsibility, not line count. Check `DocumentService` and `DocumentPromotion` are each describable without "and"; that `read_mappers.py` holds mapping only (no queries); that the rule of three holds for the identity cache (user and machine, two arms, no third helper); that no mapper is a one-line pass-through; no new `Any` (the `jwt.decode` result is `Any` only inside PyJWT's stubs; our signature takes `object`); every new public symbol has an imperative docstring; remove the `D` and `ANN401` baseline entries of every file rewritten (`auth/*`, `documents/service.py`, `schema/discovery/*`, `pipeline_rows.py`). `app.features.documents.service` is in the mypy `ignore_errors` override (`pyproject.toml:86-92`): the new `promotion.py` is checked in full, and `service.py` should be run with its entry temporarily removed locally; the config edit is G2's. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with before and after `measure_code_rules.py` numbers (`DocumentService` 179 lines and `DiscoveryMachineService` 102 are informational).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_auth_request_resolution.py tests/test_principal.py tests/test_role_guards.py tests/test_guard_session.py \
  tests/test_jwt_verifier.py tests/test_current_user.py tests/test_me_endpoint.py tests/test_document_service.py \
  tests/test_document_conflicts.py tests/test_discovery_admin_pipeline.py tests/test_discovery_service_errors.py \
  tests/test_discovery_entity_dedup.py tests/test_suggestion_service.py tests/test_promote_new_document.py \
  tests/test_promote_requirement_edge.py tests/test_vote_endpoints.py
cd ../..
./ci.sh
```

Run `tests/test_discovery_admin_api.py` and `tests/test_discovery_coverage.py` in the background (slow). Also `cd apps/web && npm test -- DiscoveryPipelinePage` to confirm the `Z` timestamps.

## Parallel notes

Runs in batch 2 alongside T1 step 2, B2, B4, I1, I2, W3, W4. Do not touch `features/discovery/{stage_sync,task_enqueue}.py` or the `stage_of` function in `pipeline_rows.py` (B4 owns those; this chapter only deletes the four `*_dict` functions at the top of that file, a disjoint hunk, and the module docstring line 1 becomes stale: whoever merges second fixes it). Do not touch `features/discovery/*_controller.py` signatures (B5, after this chapter). The suggestions files in the table are B2's: do the suggestions retype (step 7) only after B2 is merged, and keep every earlier step out of `features/suggestions/`. This is an addition to the touches table. `features/discovery/emit*.py` were restructured by A2 (merged first). A docstring-only pass (T1 step 2) over `features/auth`, `features/documents` or `schema/discovery` must not run concurrently: schedule it after this chapter.
