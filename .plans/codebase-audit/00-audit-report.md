---
name: Codebase audit — Audit report
overview: "Smell-first audit of apps/api, apps/discovery-ingest and apps/web with the refactoring skill: baseline, verdict, findings by ID, what to leave alone, and the typing design for the Any sites."
isProject: false
---

# Codebase audit — Audit report

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/) · **Ledger:** [run-ledger.md](run-ledger.md)

---

## 0. Method and scope

A previous pass, [code-rules-remediation](../code-rules-remediation/00-architecture.md) (chapters 0-11, merged), cleaned `apps/api` and `apps/web`. It excluded `apps/discovery-ingest` and closed with recorded size exceptions. This audit is a fresh pass over all three code areas on 2026-11-02 against `main` at `0e713cc`.

- Baseline numbers come from `apps/api/scripts/measure_code_rules.py` and `ruff --select D --isolated --statistics`.
- Three read-only smell scans (API, ingest, web) were run against the refactoring skill's `smells.md` plus `code-structure.md` and `refactor-step.md`.
- The highest-severity claims were then checked by hand. **v** marks a finding that was independently verified. Findings without **v** come from the scans only and are re-measured at the start of the chapter that touches them.
- `apps/mobile` holds only `lib/providers`; nothing to audit.

Size is judged as a rule of thumb for single responsibility ("describable without 'and'"), not as a hard line count (decision U2 in [gaps-and-decisions.md](gaps-and-decisions.md)).

## 1. Baseline

| Area | Non-test LOC | Classes >100 (info) | Methods >5 lines (info) | Params >3 | pydocstyle `D` violations today |
| --- | --- | --- | --- | --- | --- |
| `apps/api/app` + `scripts` | 15.4k | 7 + 1 | 444 + 72 | 38 + 10 | 367 with default rules (D102 x156, D103 x67, D100 x41, D202 x27, D107 x26, D101 x17, D104 x11, other 22); 361 with `convention = "pep257"`; 330 after the D202/D209 autofix |
| `apps/discovery-ingest` | 11.5k | 2 | 409 | 47 | 28 with default rules (D107 x14, D401 x8, other 6); 27 with `pep257`; 25 after autofix |
| `apps/web/src` | 13.2k | not measured | n/a | n/a | n/a (TSDoc is out of scope here) |

- `Any` appears 21 times in API and 67 times in ingest; web has zero `any` and zero `@ts-ignore`.
- Tooling gaps: API ruff selects `E,F,W,I,UP,B,SIM` only (no `D`, no `ANN401`); API mypy is `strict = false` with `ignore_errors` on four modules plus all of `scripts.*`; the web ESLint config has no `no-restricted-imports` rule (`architecture.test.ts` covers part of this).
- Largest files: `ingest/cli.py` 540 lines, `scripts/import_openplz_locations.py` 403, `scripts/seed_data/taxonomy.py` 385, `ingest/api_client.py` 372, `web/features/discovery-admin/types/index.ts` 353.
- The ingest CLI is a **public interface**: `.github/workflows/discovery-*.yml` and `docs/operations/` call `python -m discovery_ingest <group> <command> --flags` (for example `budget show --require-remaining ...` with exit code 3, `govdata fetch`, `worker drain`, `llm probe`, `artifacts list/download`, `fim probe`). Any CLI rework keeps command names, flags and exit codes.

## 2. Verdict

The layering from the previous remediation holds up: domain registries, outcome lookups and the architecture test are good. The real problems are not line counts. They are:

1. **Correctness defects**: error paths that return 500 or leave state open (C1-C3), and fixture rows from the tests still sitting in the production location list (C8).
2. **Under-shared logic that has already drifted**: locale picking, enrich flows, emit flows, hand-mirrored DTOs.
3. **`apps/discovery-ingest` was never remediated**: a 540-line `cli.py` that mixes parsing, orchestration and rendering, and 15 copies of one HTTP block.
4. **Typed-boundary erosion**: `Any` in ingest, `as T` in web, hand-written types that mirror backend schemas.
5. **No tooling that keeps it honest**: no docstring rule, no `Any` rule, a hand-synced CLI table.

## 3. Findings

Grouping implies severity: Correctness is fixed first, the rest in the main wave, "Low and hygiene" opportunistically. The chapter that owns each ID is listed in [01-rollout.md](01-rollout.md) (finding-to-chapter map).

### 3.1 Correctness

| ID | Smell | Evidence | Why it matters |
| --- | --- | --- | --- |
| C1 v | Divergent Change / swallowed error path | `voting/service.py:82` -> `SuggestionService.transition_to` -> `handlers.promote`. `PromotionConflictError` (`suggestions/handlers.py:30`) and `AlreadyDecidedError` (`transitions.py:17`) extend `ValueError`. `voting/controller.py:35` catches only `NotFoundError`, `SelfVoteError`, `SuggestionNotVotableError`; `_STATUS_BY_ERROR` (`suggestions/controller.py:29`) omits both; `main.py:42` only installs object-store handlers; `transitions.py:56` raises a bare `ValueError` for "not found". | A promotion race while voting returns 500 and `provide_session` rolls back the user's vote. The only tests of `PromotionConflictError` are in `test_promote_requirement_edge.py`. |
| C2 v | Inconsistent error handling / duplicated flow | `discovery/emit.py:_create` calls `suggestions.create` with no handling; `candidate_emit.py:83-105` converts `DuplicateSuggestionError` and `UnknownTaxonomyCodeError` into `EmitSkip`. | On the claim-emit path one duplicate or bad taxonomy code aborts the whole catalogue batch. The two emit services duplicate tally, skip builders and idempotency-key helpers. No test references `DiscoveryEmitService` by name, but `test_discovery_emit.py` covers the flow with 5 HTTP tests (none for the duplicate or bad-code path). |
| C3 v | Swallowed error / resource lifecycle | `ingest/worker/run.py:63-76` closes a run only on `DiscoveryMachineApiError`. | Any other exception (handler bug, `httpx.HTTPError`, `ValidationError`, Ctrl-C) leaves the run open forever. |
| C4 | Swallowed errors | `ingest/cli.py` (`except` at lines 88, 168, 202, 331 in `_govdata_run`, `_pvog_run`, `_fim_enrich`, `_leika_enrich`) return 1 on `DiscoveryMachineApiError` without printing it although `cli_errors.failing_with_api_error` exists (`govdata fetch` does print it); `pvog/client.py:110-125` and `govdata/ckan.py:92-99` let raw `httpx.HTTPError` and `ValueError` escape; no retry or backoff on any crawl client. | Operators get a bare exit code or a traceback. |
| C5 | Resource lifecycle | `ingest/worker/llm_setup.py`, `extract/llm/evaluation/command.py:53` and `browser/client.py:51` create `httpx.Client` objects that are never closed. | Leaked connections in long drains. |
| C6 | Swallowed exception | `api/lifespan.py:24` `except Exception: return set()`. | A dead DB at boot silently becomes `{"de","en"}`; locales added later are never picked up. |
| C7 | Missing guard | `voting/service.py:46` (`VoteService.remove`) never checks the suggestion is still pending; `_get_pending` is a plain read with no row lock. | Removing a vote after a decision changes a final tally; concurrent casts can race. |
| C8 | Leaked test data in production | **Found by the live check on 2026-11-02:** `GET https://redtape.cc/api/v1/districts?state=14` returns `146 · Kreis Beispiel` and `GET /cities?district=146` returns `14612 · Musterstadt`, the fixtures from `tests/test_fix_saxony_jurisdiction_leak.py` and `tests/test_locations_repository.py` that the Saxony repair names as leaked. The real tree (13 districts, Dresden `14612000`) is present, and a scan of the other 15 states found nothing similar. | Users of the location picker see two fake places; anything attached to them points at a place that does not exist. |

### 3.2 Duplicated and under-shared logic

| ID | Smell | Evidence |
| --- | --- | --- |
| D1 | Duplicated Code (locale, 3 copies) | `i18n_resolution.pick_i18n` (de-fallback order), `locations/service._pick_i18n:11-29` (an identical algorithm, so deleting it changes nothing), `suggestions/slugs.pick_title:12` (en-first order). **Correction:** `pick_title` is not a display picker. It builds slugs (`Document.slug` and the candidate dedup key via `candidate_key`), so converging its order would change durable IDs. Chapter B1 routes it through the shared code but keeps its order. |
| D2 | Data Clumps (locale carrier) | `shared.locale.ResolvedLocale`, `documents.document_read.Locales`, and about 41 loose `locale` + `enabled_locales` pairs; the `("de","en")` default is hard-coded in 4 places. |
| D3 | SQL in a controller | `api/routes.py:19-48` runs `select` in route handlers, reads `request.state.locale` with its own `"de"` default, returns `dict[str, Any]`, and has no tests. |
| D4 | Duplicated Code, Large Class | `ingest/api_client.py` (`DiscoveryMachineClient`, 295 lines): 15 `with httpx.Client(...)` blocks (14 methods plus `_call` itself); `_call` serves 14 operations (10 directly, 4 via `_budget_call`) while the rest repeat the block; new TCP/TLS per request; hard-coded `timeout=60.0`; `_call` takes 7 parameters. |
| D5 | Divergent Change, Repeated Switches | `ingest/cli.py` (540 lines): `_build_parser` is 139 lines; govdata/pvog/fim/leika/worker handlers, mapping loops and drain wiring sit beside parsing; `_COMMANDS` is hand-synced with the parser; it imports private names `_post_catalogue_batches` and `_map_govdata_record`. Eight sibling modules use `register_*_parser`, a pattern the main file does not follow. |
| D6 | Duplicated Code, Shotgun Surgery | FIM and Leika enrich: `cli._fim_enrich` and `_leika_enrich` (~30 lines each), parallel pairs in `enrich.py:75-134`, and a third copy of the FIM flow in `worker/enrich_metadata.py`. A new source touches all three. |
| D7 | Duplicated Code (drift risk) | `ingest/schemas.py` plus `artifacts.py`, `mentions.py`, `edges.py`, `emit_models.py`, `budget_models.py`, `candidate_sources.py` hand-copy `api/app/schema/discovery/machine.py` (`StopReason`, `DiscoveryTaskKind`, ...). A new value on one side is silently rejected on the other. **Real drift found:** ingest `RunFinishRequest` lacks the API's `ge=0` bounds on the five counts and `max_length=1000` on `error_detail`; the other 39 model pairs match today. The API's `BudgetRead.resource` is a plain `str`, so a new `BudgetResource` value would break ingest silently (chapter I5 compares via an exported enum list). |
| D8 | Duplicated Code | `_optional_str` in 3 ingest modules; `FEDERAL_ARS` in 2; page and record caps hand-rolled in `pvog/client.iter_records` and `govdata/ckan.iter_record_pages`; `_*_for_row` key ladders in both mappers. |
| D9 | Duplicated Code / bypassed settings | `ingest/cli.py:208` reads `BOT_CONTACT_URL` via `os.environ.get(.., DEFAULT_BOT_CONTACT_URL)` instead of `IngestSettings.bot_contact_url`; the FIM base URL is hard-coded in 4 places (`worker/enrich_metadata.py:18`, `fim/client.py:26`, `leika/client.py:24`, `cli.py:471`) although `fim_portal_base_url` exists; `browser probe` ignores `BOT_CONTACT_URL` entirely; `cloudflare_account_id` is declared in both `BrowserSettings` and `LlmSettings`. |
| D10 v | Duplicated Code, Shotgun Surgery (web) | 12 `accessToken!` assertions across 12 discovery-admin hooks, each repeating `useLocale` + `useAuth`, plus 7 `candidateId!`/`catalogueId!` assertions and a `session!` in the probe hook; 13 `discoveryAdminApi.ts` service functions repeat `{locale, accessToken}`. |
| D11 | Duplicated Code (web) | List-query triplets `{candidate,task,catalogue}ListQuery.ts` plus three one-line `use*ListState` wrappers; three table wrappers differing only in namespace, icon and columns. |
| D12 | Duplicated Code (web) | Four panels (`DocumentEmitPanel`, `EmitPreviewPanel`, `DocumentEdgesPanel`, `ArtifactsPanel`) repeat the same loading/error branches; 5 live discovery-admin loading-text sites lack `role="status"` (the only text site that has it is the dead `DiscoveryCatalogueQueryStatus`). |
| D13 v | Duplicated Code, Insider Trading (web) | `formatRetryAfter.ts` and `suggestions/utils/formatRelativeTime.ts` are near-clones; `taskColumns.tsx:3` imports from the suggestions feature via a relative path, so `architecture.test.ts` misses it. |
| D14 | Duplicated Code (web) | `RequireAuth.tsx:12-26` and `utils/discoveryAdminGuardOutcome.ts:25-31` map `AuthStatus` independently; `RequireAuth.tsx:22` casts `role as MinRole`. **Corrections:** the disagreement on `unconfigured` is intentional and covered by tests; `RequireAuth` is used by no route (only its test, and `STATUS.md` lists it as delivered); it has a latent bug, `admin` is missing from `ROLE_RANK`, so an admin gets a blank page on a moderator route. Chapter W2 shares the status lookup and fixes the role table red-first; deleting `RequireAuth` is the operator's call. |
| D15 | Duplicated Code (scripts) | `UUID_NAMESPACE` and `_stable_uuid` in both `import_openplz_locations.py` and `cleanup_openplz_data.py`; `fix_saxony_jurisdiction_leak.py` is a one-shot repair that `start.sh` runs on every boot. |

### 3.3 Type-boundary erosion (design in section 5)

| ID | Smell | Evidence |
| --- | --- | --- |
| T1 | Primitive Obsession (web) | `services/api.ts:79` returns `(await res.json()) as T`; `discovery-admin/types/index.ts` (353 lines) hand-writes backend shapes; some wire fields are plain `string`. `apps/web/package.json` has no runtime validator (`ajv` is only a transitive ESLint dependency), and the API serves `/schema/openapi.json`. Chapter W3 therefore guards the boundary with a committed OpenAPI snapshot plus a contract test, and keeps the single documented `as T`; it does not validate at runtime. |
| T2 | Duplicated Code (web) | Each string union is declared twice (type in `types/index.ts`, array in `types/listValues.ts`); `satisfies` checks membership, not coverage, so a new backend value compiles but never reaches the filters. |
| T3 | Primitive Obsession (web) | `useSuggestionFilters.ts:19` casts `params.get("status") as SuggestionStatusFilter`; a bad `?status=` reaches the API unvalidated. |
| T4 | Primitive Obsession (ingest) | 67 lines containing `Any` including imports (53 without), mostly raw JSON rows (`pvog/client.py` 14, `govdata/client.py` 8, `enrich.py` 7, `govdata/ckan.py` 6, `extract/llm/*` 10 non-import lines); every mapper repeats `isinstance` ladders. |
| T5 | Primitive Obsession (API) | Skip reasons are bare strings (`"not_found"`, `"duplicate"`, `"invalid_payload"`, `"already_emitted"`, `"missing_entity"`); `CataloguePipelineResponse.entities/fetch_logs/claims/events` are `list[dict[str, object]]`; `KindHandler` takes `payload: Any`; `openplz_client.py` has 12 lines with 19 `Any`, although the typed DTOs already exist in `app/schema/openplz.py` and the importer validates items itself; `routes.py` and `auth/jwt.py` use `dict[str, Any]` (a `TokenClaims` dataclass already exists, the `Any` is only in `_build_claims`). |
| T6 | Primitive Obsession (ingest) | `_BASE_HANDLERS: dict[str, TaskHandler]` is keyed by raw `str` instead of `DiscoveryTaskKind`; `discovery_api_key` is a plain `str` (Cloudflare tokens use `SecretStr`); `DiscoveryMachineApiError` embeds `response.text` verbatim and `cli.py` prints it. |

### 3.4 Layering and design

| ID | Smell | Evidence |
| --- | --- | --- |
| L1 | Repeated Switches (API) | `SubmitterRef.kind: Literal["user","crawler"]` is switched on at `suggestions/service.py:49-50,174,179,195-196,232-233` and duplicates the auth `Principal` types. |
| L2 | Data Clumps (API) | Suggestion filter fields (`status`, `kind`, `source_type`, `jurisdiction_id`) are unpacked across `_apply`, `count`, `list_page` (6 params), `SuggestionFilters`, `_FilterKwargs` and `_filter_kwargs`. |
| L3 | Repeated full-list load per write (API) | `stage_sync.derive_stage_for:17-28` loads full task, fetch-log and claim lists just to `len()` them. **Correction:** this is not a classic N+1. `enqueue_task_if_needed` never returns `None`, so `advance_stage` runs for every batch item that has a portal URL, and appending N claims to one catalogue row reads O(N²) claim rows. Claims cannot become a pure count because resolvability inspects payloads. |
| L4 | Over-fetch (API) | `DocumentService.find_conflicts:163` -> `list_slugs_and_urls` reads every document of the jurisdiction and normalises URLs in Python on each create, preview and promote; `Suggestion` already stores `normalized_url`. Needs a migration, so optional and separate. |
| L5 | Layering inversion (API) | `schema/discovery/read.py` imports ORM models at line 10 and its `from_row` factories use them (lines 46, 90, 247, 305 are the `@classmethod` decorators); the same applies to `schema/suggestion/read.py`, which imports the ORM class `Suggestion`; `schema/discovery/candidates.py:10` imports `features.suggestions.slugs.pick_title`; `discovery/url_normalize.py` imports `schema.suggestion.payload`. |
| L6 | Divergent Change (API) | `DocumentService` (179 lines) mixes reads, tag resolution, requirement creation, duplicate detection and jurisdiction lookup; promotion write logic leaks into it; `source="community"` is a magic string; `handlers.py` depends on the concrete class. |
| L7 | Duplicated work (API), partly wrong in the scan | **Corrected:** the duplicate verification is real only for the three machine endpoints that take `machine_principal` (claim, catalogue emit, candidate emit): the API key is verified once in the guard session (`guard_session.py:57-63`) and again in the request session. Discovery admin routes verify the JWT once; `/me`, voting and suggestions use no guard; `require_role` is used by no production route (only `test_role_guards`). Litestar guards run before dependency injection, so a second session cannot be removed without touching `app/db.py`; chapter B3 removes the duplicate verification instead. `auth/dependencies.py:20,40` keeps a mutable `global _jwt_verifier`, lazily built and not thread-safe. |
| L8 | Layering inversion (web) | Shared `services/api.ts:2` imports `features/auth/contexts/AuthContext`; `useApi()` is used only by `useLocalesQuery`. |
| L9 | Mixed concerns (web) | `DiscoveryDocumentPage` runs 5 queries and builds 4 prop-slots; `DiscoveryPipelinePage` runs 3 queries with two `ReactNode`-returning helpers. |
| L10 | Dual surface (API) | Candidate and task list endpoints (discovery admin) accept legacy params beside canonical `list_query`; `list_candidates` has 8 params (`LEGACY_SORTS` merge). **Correction:** the machine `GET /candidates/` params `status` and `min_mentions` are not legacy and stay, because the ingest client uses them. |
| L11 | Hidden dependencies (API) | `DiscoveryMachineService.__init__` builds `CatalogueUpsertService`, `TaskQueue`, `ClaimIngest`; `SuggestionService` builds its own handlers and transitions. |
| L12 | Divergent Change (ingest) | `fim/client.py:20-48` and `leika/client.py:19-42` mix fixture and live HTTP transport behind `if self._fixture is not None`. |
| L13 | Long Parameter List (ingest) | `run_worker_drain` 11 params, `harvest/pvog._draft` 9, `run_recorded_drain` 7; `browser`, `llm`, `after_extract`, `llm_enqueue` travel together; the same five PVOG hint values pass through two layers. |
| L14 | Long Parameter List (API) | `list_candidates` 8, `select_candidate_sources` 6, `suggestions/repository.list_page` 6, `admin_controller.list_tasks` 6; the list is incomplete: `list_catalogue`, `select_candidates` and `list_artifacts` also exceed three. |

### 3.5 Low and hygiene

- **Dead code** (**v**): `web/features/discovery-admin/components/DiscoveryCatalogueQueryStatus.tsx` has no importer.
- **Dead parameters:** `reason` in both `SuggestionService.transition_to` and `SuggestionTransitions.transition_to`; `NewRequirementHandler.__init__(taxonomy)`. (`NewDocumentHandler.validate(jurisdiction_id)` is not dead: the `KindHandler` protocol requires it and `NewRequirementHandler` uses it.)
- **Unowned layering violations found while sizing T3:** web `components/layout/menu/{ProfileMenuRow,DocumentsMenuRow}.tsx` import from `features/`; API `shared/list_query/errors.py` imports `litestar.ValidationException` and `candidates/service.py` and `discovery/candidate_list_items.py` call `raise_if_any`, so services raise HTTP exceptions; `schema/discovery/artifacts.py` imports litestar `UploadFile`; `shared/locale.py` imports `Request`. They go on the T3 allow-list and are removed by the chapters named there.
- **One-line delegations worth inlining:** `SuggestionService.get`, `get_document_jurisdiction`, `requirement_exists`, `requires_directly`; `VoteService.tally_for`/`tally_for_many`; ingest `_post_catalogue_batches`, `_budget_call`, `_budget_allows_fetch`; web `use{Candidate,Task,Catalogue}ListState`, `useCatalogueState`.
- **Misplaced:** `api/app/services/openplz_client.py` (131-line class) is imported only by `scripts/`.
- **Web consistency:** empty-value placeholder `"—"` vs `"-"` (`runGroups.ts`); raw enum values in `taskColumns.tsx:53,67` and `candidateFilters.ts:60` although `translateOrRaw` exists (the label fix changes both the web fallback JSON and `apps/api/scripts/seed_data/translations/*.json`, so it needs the operator's yes); the hard-coded "Redtape" in `LoadingShell.tsx:30` is a proper noun in a pre-i18n shell and is left alone; duplicate `FilterOption`; `as Record<string, number>` casts in `coverage/contentGroups.ts:30` and `runGroups.ts:21`; `app/queryKeys.ts` `suggestions.list` takes 4 positional params.
- **Test-coverage gaps, after verification in chapter G1:** the scans listed more than are real. `DiscoveryEmitService` and `advance_stage`/`derive_stage_for` are covered through HTTP tests (the failure branches belong to A2 and B4); `/locales` and `resolve_locale` are covered by B1; `cli._build_parser` is referenced by `test_cli_worker*.py`; the admin hooks and `discoveryAdminGuardOutcome` are covered by W1 and W2. What G1 still writes: web `safeHttpUrl` (security-relevant, **v**), `hostOf`, `localizedTitle`, `translateOrRaw`; API `seed_i18n`; and a CLI-versus-workflow contract test. Side finding: only `DocumentHeader` uses `safeHttpUrl`; `OfficialSourceSection`, `NewDocumentPayloadView` and `CandidateSources` render API URLs as `href` without it (the API validates submitted URLs, so this is defence in depth).
- **Open size observations from the previous ledger** (informational): `DocumentRepository` 187 lines, `DocumentService` 179, `SuggestionService` 124, `OpenPLZClient` 131, `Settings` 117, `DiscoveryMachineController` 125, `DiscoveryMachineService` 102, `EvalRunner` 117. They are addressed only where a responsibility split (L6, L11) is wanted anyway.
- **Stale docs:** `docs/planning/STATUS.md` still lists the deleted `LocaleContext.tsx.draft` as dead.

## 4. Leave alone

- API: `suggestions/handlers.py` `KIND_HANDLERS` registry; `transitions.py` as sole owner of `status`; domain errors mapped in controllers (no `HTTPException` in services); `StrEnum` discovery enums with `PipelineStage.rank`; `fanout.py` rule tuple; `ApiKeyService` (SHA-256, `compare_digest`, unknown and revoked indistinguishable); `db_headroom` and `budget_meter` deliberate fail-open and fail-closed; `provide_session` as the single commit and rollback point.
- Ingest: `extract/llm/*`, `worker/*` and `browser/*` are well split; `DrainPolicy`, `Tally`, `StopReason`; `PoliteUrlFetcher` SSRF, robots, pacing and byte-cap handling; secret scrubbing in `browser/client.py` and `redaction.py`; no subprocess or mutable-global hazards.
- Web: `architecture.test.ts`; the validated `services/listQuery` + `useListQueryState`; the `QueryStatus` object; `GUARD_VIEWS`; the DataTable capability model; near-zero `any`; strong test infrastructure.
- Long-but-linear methods that are one responsibility (for example `OpenPLZClient.iter_paged`, `create_app`): not worth chasing.

## 5. Typing design for the `Any` sites

Principle: type the boundary once, then pass typed values inward. Three tools, in this order of preference:

1. **A Pydantic model** at an HTTP or file boundary where specific keys are consumed (parse once, `extra="ignore"`, optional fields explicit). This deletes the `isinstance` ladders.
2. **A `TypedDict`** (`total=False` where keys are sparse) where values are only read and never validated, for tiny payloads such as chat messages.
3. **`pydantic.JsonValue`** (the recursive JSON alias already in the dependency) with local aliases `JsonObject = dict[str, JsonValue]` for genuinely open JSON (JSON Schema documents, opaque request bodies). Never bare `Any` or `object`.

| Site | Today | Target type |
| --- | --- | --- |
| `ingest/pvog/client.py` (14), pvog mapper ladders | `dict[str, Any]` rows, `list[Any]` nodes | `PvogFacade`, `PvogPage`, `PvogRecord` Pydantic models parsed in `_fetch_page`; `_dict_records`, `_lb_id_for_record`, `_first_leika_key`, `_title_for_row` become model properties |
| `ingest/govdata/client.py` (8), `govdata/ckan.py` (6) | `dict[str, Any]` | `CkanPackage`, `CkanResource`, `GovDataRow` models; the CKAN envelope as `CkanResponse` |
| `ingest/fim/client.py`, `leika/client.py`, `enrich.py` (7), `worker/enrich_metadata._parse_steckbrief_body` | `dict[str, Any]` steckbrief/stammtext | `Steckbrief` and `Stammtext` models (only the keys we read); `_first_text` becomes a method |
| `ingest/extract/llm/schema.py`, `schema_prep.py`, `payloads.py`, `cloudflare.py`, `client.py` | `dict[str, Any]` schemas and bodies; `_resolve(node: Any) -> Any` | `JsonSchema = JsonObject` alias, recursive helpers typed over `JsonValue`; `Body = JsonObject`; `ChatMessage = TypedDict(role, content)` replacing `dict[str, str]` |
| `ingest/capture_requeue.py:31` | `Sequence[Any]` argparse action | disappears with the Typer CLI (chapter I4) |
| `api/features/suggestions/handlers.py:49-53` | `payload: Any` | `KindHandler[PayloadT](Protocol)` with `PayloadT` bound to the per-kind Pydantic payload models in `schema/suggestion/payload.py` |
| `api/features/auth/jwt.py:45` | `dict[str, Any]` claims | `JwtClaims` Pydantic model (`sub`, `email`, `user_metadata.full_name`), validated once in `_build_claims` |
| `api/routes.py` | `list[dict[str, Any]]`, `dict[str, Any]` | `LocaleRead` and `TranslationBundle` response models in the new `locales` feature |
| `api/services/openplz_client.py` (11) | `Any` payloads, `Callable[[Any], T]` | one Pydantic model per OpenPLZ endpoint (`FederalState`, `District`, `Municipality`, `Locality`); the three `_handle_paged_*` methods collapse into one parse of `RootModel[list[T]]` or `{"items": list[T]}` |
| `api/schema/discovery/read.py:225-228` | `list[dict[str, object]]` | typed `PipelineEntityRow`, `FetchLogRow`, `ClaimRow`, `EventRow` read models |
| `web/services/api.ts:79` | `(await res.json()) as T` | decision D1: a `parse` function per endpoint (Zod-style) or generated types; derive unions from arrays (T2) |

Gate (chapter T2): ruff `ANN401` alone is too narrow, because it flags only `Any` in signatures (10 hits in API, 3 in ingest, against about 90 `Any` uses). T2 therefore adds a `TID251` ban on `typing.Any` with a per-file baseline (5 API files, 14 ingest files) next to `ANN401`, and each typing chapter removes its entries so the count only goes down. mypy `disallow_any_explicit` is enabled for `discovery_ingest` only (it needs `pydantic.mypy`); in `apps/api` it reports 133 mostly false positives on `class X(BaseModel)` with the locked pydantic and is not used there.

## 6. Corrections to the raw scans

- The scan said `cli.py` reads `os.environ["BOT_CONTACT_URL"]`; it uses `os.environ.get(..)` with a default. The bypass of settings is still real.
- The chapter authors re-read the code and corrected the scans: L3 is repeated full-list loading rather than N+1; L7 applies only to the three machine endpoints; `pick_title` builds slugs and must keep its order; `NewDocumentHandler.validate` is not a dead parameter; machine `GET /candidates/` params are not legacy; several test gaps do not exist (see 3.5). These corrections are folded into section 3 above.
- Some line numbers in the scans were stale; section 3 now carries the verified ones. The owning chapter re-measures its numbers first anyway.
