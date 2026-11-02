---
name: "Chapter I2 — Ingest typing"
overview: "Replace the raw-JSON dict[str, Any] sites of discovery-ingest with Pydantic models parsed once at the boundary, a JsonValue-based alias for open JSON and a ChatMessage TypedDict; key the handler table by DiscoveryTaskKind; share the lenient-text helpers."
todos:
  - id: characterize
    content: "Pin every mapper, parser and schema helper against the real fixtures before any type changes"
    status: pending
  - id: shared-helpers
    content: "Add json_types, lenient and catalogue_scope; delete the three _optional_str copies and the FEDERAL_ARS duplicates"
    status: pending
  - id: crawl-models
    content: "PVOG, GovData/CKAN and FIM/LeiKa models; clients and mappers consume them"
    status: pending
  - id: llm-json
    content: "JsonSchema alias, ChatMessage TypedDict, JsonValue-typed schema_prep, payloads and clients"
    status: pending
  - id: handler-keys
    content: "Handler table keyed by DiscoveryTaskKind with a coverage test"
    status: pending
isProject: false
---

# Chapter I2 — Ingest typing

**Repo:** `redtape` · **Branch:** `refactor/ingest-typing` · **Status:** planned

**Depends on:** A3 (ingest run lifecycle) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) T4, T6, D8 and section 5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `ingest/{pvog,govdata,fim,leika,enrich.py,extract/llm}` (rollout table); this chapter also edits the lines listed under "Files outside the touches set".

**Findings:** T4, T6 (handler keys), D8 (shared helpers, `FEDERAL_ARS`), hygiene `_budget_allows_fetch`.

## Goal

No `Any` in the ingest crawl, enrich and LLM-JSON code. Each external payload is parsed once into a Pydantic model that holds only the keys the code reads; mappers consume the model, not a dict with `isinstance` ladders. Open JSON (JSON Schema documents, request bodies) is `pydantic.JsonValue` through a local alias. The task-kind handler table is keyed by `DiscoveryTaskKind`. Mapper output (`CatalogueBatchItem.raw_payload`, claim payloads, `external_id`) is byte-identical to today's.

Typing rules from [../00-audit-report.md](../00-audit-report.md) section 5 apply in this order: Pydantic model, then `TypedDict`, then `JsonValue`. No bare `Any`, no `object` standing in for JSON, no silencing `cast` or `# type: ignore`.

Verified: `pydantic.JsonValue` imports in the pinned pydantic (`uv.lock` has 2.14.1; `pyproject.toml` allows `>=2.10,<3`); it is already used in `browser/client.py`, `extract/llm/{payloads,envelope,classify}.py`.

## Acceptance number

`grep -rn "\bAny\b" apps/discovery-ingest/discovery_ingest --include=*.py` counts lines (import lines included). Measured at `0e713cc`:

| File | Lines with `Any` (all / excluding import) | After I2 |
| --- | --- | --- |
| `pvog/client.py` | 15 / 14 | 0 |
| `govdata/client.py` | 9 / 8 | 0 |
| `govdata/ckan.py` | 7 / 6 | 0 |
| `enrich.py` | 8 / 7 | 0 |
| `fim/client.py` | 3 / 2 | 0 |
| `leika/client.py` | 3 / 2 | 0 |
| `extract/llm/schema.py` | 3 / 2 | 0 |
| `extract/llm/schema_prep.py` | 4 / 3 | 0 |
| `extract/llm/payloads.py` | 3 / 2 | 0 |
| `extract/llm/cloudflare.py` | 3 / 2 | 0 |
| `extract/llm/client.py` | 2 / 1 | 0 |
| `worker/enrich_metadata.py` | 2 / 1 | 0 |
| `cli.py` (two mapper helper signatures) | 3 / 2 | 0 |
| `capture_requeue.py` (argparse action; goes away in I4) | 2 / 1 | 2 (I4) |
| **Total** | **67 / 53** | **2** |

The PR records the same command before and after. The audit report quotes 14 (pvog), 8 (govdata client), 7 (enrich), 6 (ckan) and 12 (`extract/llm/*`); those are non-import lines except the last, which measures 10 non-import lines (15 with imports) across the five `extract/llm` files above. Use this table as the baseline.

## Verified payload shapes (the keys the code actually reads)

All keys come from reading the current code and the fixtures under `tests/fixtures/{pvog,govdata,fim,leika}`.

### PVOG Suchdienst (`pvog/client.py`)

| Payload | Keys read | Fixtures |
| --- | --- | --- |
| bootstrap (facades) | `facades.personalMatters[]` with `code`, `children[]` (recursive); a node with non-empty `children` is not a leaf; leaf `code` is stripped, blanks dropped; result `sorted(set(...))` | `facades_personal_matters.json`, `facades_cli_single_leaf.json` |
| search page | `serviceDescriptions.content[]` (non-dict entries dropped), `serviceDescriptions.last` (`bool(...)`, default `True`); a page without `serviceDescriptions` is `([], True)` (legacy `content` at top level is ignored, see `test_pvog_client.py:87`) | `v7_page_*.json`, `page1-3` |
| record (row) | `id`, `lbId`, `leikakeys[]`, `leikaIds[]` (first non-blank entry), `onlineServiceLinks[].uri`, `sourcePortals[].uri` (first non-blank, in that field order), `title`/`name`/`leistungsname` (first non-blank, in that order), `description`/`beschreibung`/`teaser` | `live_shape_row.json`, `v7_page_*.json` |

The whole row is also stored verbatim as `raw_payload` (plus the reserved `_personal_matter_code`). The model therefore keeps the untouched row next to the typed fields.

Quirk to pin, not fix: the dedupe key `_lb_id_for_record` accepts only `str` `id`/`lbId`, while `_external_id_for_row` coerces any non-`None` value with `str()`. A row whose `id` is an integer is dropped by `iter_records` today but would map if read directly. Keep both behaviours: the record exposes `dedupe_id` (string-only) and `lb_id` (coercing). The PR notes the difference for the operator; whether to unify is outside this chapter.

### GovData OZG feed and CKAN (`govdata/client.py`, `govdata/ckan.py`)

| Payload | Keys read | Fixtures |
| --- | --- | --- |
| OZG page / feed page | `content[]` (must be a list in `GovDataOzgClient.from_json_file`, else `ValueError("expected top-level 'content' array in OZG JSON")`; `_content_records` returns `[]` for a non-list; non-dict entries dropped) | `ozg_page.json`, `open_pvog_live_shape.json` |
| OZG row | `leika_key`, `ozgid`, `id` (external id, first non-blank); `ars` (`None`/blank/`000000000000` is federal, anything else raises `GovDataMappingError`); `leika_name`, `leistungsname`, `title`, `name`, `leika_bezeichnung`, `ozg_bezeichnung` (title ladder); `beschreibung`, `description`, `leika_bezeichnung`, `ozg_bezeichnung` (description ladder); `url` | same |
| CKAN `package_show` | `result` (object, else `GovDataCkanError("CKAN package_show response missing result object")`), `result.resources[]` (list, else `"CKAN package has no resources list"`), per resource `id`, `name`, `url` | `package_show.json` |

Real-shape fact: the live row has `ozgid` as an **integer** (`open_pvog_live_shape.json`). Text fields in these models therefore coerce non-strings with `str()` exactly like `_optional_str` does today.

### FIM steckbrief and LeiKa stammtext (`fim/client.py`, `leika/client.py`, `enrich.py`)

| Payload | Keys read |
| --- | --- |
| steckbrief | `leistungsschluessel` (required, non-blank string, else `ValueError("steckbrief missing leistungsschluessel")`; also compared with the requested key by the fixture client), label from `title`, `titel`, `leistungsbezeichnung` (first non-blank, in that order), `titel` (German title of the `new_document` claim), `kurztext` (optional `metadata` claim) |
| stammtext | `redaktion_id`, `leistung_id` (required, non-blank strings, else `ValueError("stammtext missing redaktion_id")` or `"... leistung_id"`; compared with the requested ids by the fixture client), `titel` (label and claim title), `kurztext` |

Here non-string values are **ignored** (`_first_text` requires `isinstance(value, str)`), unlike the coercing PVOG/GovData reads. The two reads stay distinct: `optional_str` coerces, `text_or_none` is string-only.

### Workers AI JSON (`extract/llm/*`)

| Site | Today | Shape |
| --- | --- | --- |
| `schema.build_json_schema` | `dict[str, Any]` from `PageExtraction.model_json_schema()`; reads `properties.domain_codes` and `properties.situation_codes`, sets `items` and `maxItems` | JSON Schema document |
| `schema_prep` | `Schema = dict[str, Any]`, `_resolve(node: Any) -> Any`; reads `$defs`, `$ref` | JSON Schema document |
| `payloads.run_body`/`chat_body`, `cloudflare._post`, `client.LlmClient.extract` | `dict[str, Any]` schema and body; `Sequence[dict[str, str]]` messages | request body (`Body` is already `dict[str, JsonValue]`) |
| messages | `build_messages`, `REPAIR_HINT`, `VIOLATION_MESSAGES` (`probe.py:29`), `worker/llm_answer.Messages` | `{"role": "system" or "user", "content": str}` |

## Target design

### Shared helpers (D8)

| New module | Contents |
| --- | --- |
| `discovery_ingest/json_types.py` | `JsonObject = dict[str, JsonValue]`, `JsonSchema = JsonObject` (a JSON Schema document), re-exports `JsonValue`; `payloads.Body` becomes an alias of `JsonObject` |
| `discovery_ingest/lenient.py` | `optional_str(value: object) -> str \| None` (the existing semantics: strip a string, `str()` any other non-`None` value, blank to `None`), `text_or_none(value: object)` (strings only), `first_present(*values: str \| None)`, and `Annotated` Pydantic types `LenientText` (coercing), `StrText` (string-only), plus `list_or_empty` / `dicts_only` before-validators that give the models the same tolerance the ladders have |
| `discovery_ingest/catalogue_scope.py` | `FEDERAL_ARS = "000000000000"` (replaces `pvog/client.py:14`, `govdata/client.py:12`, the `govdata/ckan.py:28` default; `config.py:68` default is changed in I3, which owns that file) |

`optional_str` has 3 copies (`pvog/client.py:290`, `govdata/client.py:115`, `govdata/ckan.py:151`); `first_present` replaces the ladders in 5 places (GovData title and description, PVOG title and description, LeiKa/FIM label), so both pass the rule of three.

### Models (parse once, `extra="ignore"`, `frozen=True`)

| Module | Models | Replaces |
| --- | --- | --- |
| `pvog/models.py` | `PersonalMatterNode` (`code`, `children`), `PvogBootstrap` (`facades.personalMatters`, method `leaf_codes() -> list[str]`), `PvogLink` (`uri`), `PvogRecord` (`raw: JsonObject` plus the lenient fields above; properties `lb_id`, `dedupe_id`, `leika_key`, `title`, `description`, `portal_url`), `PvogServicePage` (`content: list[PvogRecord]`, `last`), `PvogPage` (`serviceDescriptions: PvogServicePage \| None`, property `records_and_last`) | `_personal_matter_codes_from_facades`, `_collect_leaf_personal_matter_codes`, `_parse_v7_page`, `_dict_records`, `_lb_id_for_record`, `_first_leika_key`, `_portal_url_from_row`, `_uri_from_link_list`, `_title_for_row`, `_description_for_row` |
| `govdata/models.py` | `GovDataRow` (`raw`, the 13 keys above, properties `external_id_parts`, `title`, `description`, `ars`), `OzgPage` (`content: list[GovDataRow]`), `CkanResource` (`id`, `name`, `url`), `CkanPackage` (`resources: list[CkanResource] \| None`), `CkanPackageShow` (`result: CkanPackage \| None`) | `_content_records`, `_leistungen_url_from_package` ladders, govdata `_*_for_row` helpers |
| `fim/models.py` | `FimDocument` (`titel`, `kurztext`), `Steckbrief(FimDocument)` (`leistungsschluessel`, `title`, `leistungsbezeichnung`; method `label()`; classmethod `from_body(body: bytes \| None) -> Steckbrief \| None`), `Stammtext(FimDocument)` (`redaktion_id`, `leistung_id`) | `enrich._first_text`, `worker/enrich_metadata._parse_steckbrief_body`, the dict reads in `fim/client.py`, `leika/client.py`, `enrich.py` |

`raw` must be a copy of the incoming row untouched by coercion, built in the model's `mode="before"` validator, so `raw_payload` equality with the fixture holds. Property methods return `None` where a ladder found nothing; the mapper still raises `PvogMappingError` / `GovDataMappingError` with today's messages (models never raise domain errors). The mapper assigns `raw_payload: dict[str, object] = dict(record.raw)`, which type-checks because `dict()` accepts a covariant `SupportsKeysAndGetItem`; `schemas.py` is not changed.

### Client signatures after the change

- `PvogClient._fetch_page(url, model: type[M]) -> M`; `iter_records(...) -> Iterator[tuple[str, PvogRecord]]`; `map_pvog_record(record: PvogRecord, *, jurisdiction_id, personal_matter_code=None)`. A malformed body maps to the exception type A3 introduced for malformed PVOG bodies (start from A3's merged state; do not re-introduce a bare `ValueError`).
- `GovDataOzgClient.records: list[GovDataRow]`; `GovDataCkanClient.iter_record_pages(...) -> Iterator[list[GovDataRow]]`; `map_govdata_record(row: GovDataRow, *, federal_jurisdiction_id)`; the public alias `map_govdata_record` stays, the private `_map_govdata_record` import in `cli.py:38` is removed (the alias is the only name `cli.py` and the tests use).
- `FimSteckbriefClient.fetch_steckbrief -> Steckbrief`, `LeikaStammtextClient.fetch_stammtext -> Stammtext`; fixtures are validated at load time, the live body with `model_validate_json`; a `ValidationError` becomes the existing `FimClientError`/`LeikaClientError` with the existing messages.
- `enrich.py`: `fim_steckbrief_entity_request`, `fim_steckbrief_claim_requests` take `Steckbrief`; `leika_*` take `Stammtext`; `_claims` takes `FimDocument`.
- `_budget_allows_fetch` (`pvog/client.py:118`, used twice) is inlined at its two call sites. I3 later replaces both loops by `PageBudget`; do not build it here.

### LLM JSON

- `ChatMessage` is a `TypedDict` (`role: Literal["system", "user"]`, `content: str`) defined in `extract/llm/client.py` (the port). `prompt.py`, `payloads.py`, `cloudflare.py`, `probe.py:29` and `worker/llm_answer.py` (`Messages = list[ChatMessage]`, `REPAIR_HINT`) use it.
- `schema_prep`: `_resolve_object(node: JsonObject, ...) -> JsonObject` and `_resolve_value(node: JsonValue, ...) -> JsonValue` replace the single `_resolve(node: Any) -> Any`; `$defs` and each `$ref` target are narrowed with `isinstance` and a `ValueError` naming the ref when they are not objects. `copy.deepcopy(defs[name])` is redundant because `_resolve` rebuilds every container; remove it only if the characterisation test (recursive and sibling refs) passes without it.
- `schema.build_json_schema -> JsonSchema`; the two `properties.*_codes` lookups go through one narrowing helper instead of indexing `Any`.
- `payloads.run_body`/`chat_body(…, schema: JsonSchema, …)`, `CloudflareAiClient.extract(messages: Sequence[ChatMessage], json_schema: JsonSchema, *, max_tokens)`, `_post(body: Body)`, `LlmClient.extract` the same.

### Handler keys (T6)

`worker/handler_table.py`: `_BASE_HANDLERS: dict[DiscoveryTaskKind, TaskHandler]`; `_browser_handlers` and `handler_table` return `Mapping[DiscoveryTaskKind, TaskHandler]`; `worker/batch.py:34` `DrainContext.handlers` and `worker/llm_drain.py:24` `LlmDrain.handlers()` likewise. mypy now rejects a misspelt literal key.

## Files

Create: `discovery_ingest/{json_types,lenient,catalogue_scope}.py`, `pvog/models.py`, `govdata/models.py`, `fim/models.py`; tests listed below.

Edit (in the touches set): `pvog/client.py`, `govdata/client.py`, `govdata/ckan.py`, `fim/client.py`, `leika/client.py`, `enrich.py`, `extract/llm/{schema,schema_prep,payloads,cloudflare,client,prompt,probe}.py`.

Files outside the touches set (small, listed so the chief of staff can plan the merge): `cli.py` (imports at lines 38 and 41-47; `_map_govdata_records` and `_map_pvog_records` signatures and the `_map_govdata_record` call at 336-375; I1 owns the client lines, I3 and I4 own the rest), `worker/enrich_metadata.py` (`_parse_steckbrief_body`; I1 owns its client lines), `worker/llm_answer.py` (`Messages`, `REPAIR_HINT`), `worker/handler_table.py`, `worker/batch.py:34`, `worker/llm_drain.py:24`.

Read-only checks: `harvest/pvog.py`, `pvog/domain_mapping.py`, `pvog/situation_mapping.py` consume the stored `raw_payload` (`dict[str, object]`) and contain no `Any`; leave them.

Tests to update (imports of private helpers and dict arguments): `test_pvog_client.py` (imports `_parse_v7_page`, `_personal_matter_codes_from_facades`), `test_pvog_cli.py`, `test_pvog_harvest.py`, `test_govdata_client.py`, `test_govdata_ckan.py`, `test_govdata_fetch.py`, `test_govdata_cli.py`, `test_fim_leika_enrich.py`, `test_fim_steckbrief_label.py`, `test_enrich_metadata_worker.py`, `test_extraction_schema.py`, `test_llm_schema_prep.py`, `test_llm_client.py`, `test_cli_worker_llm.py`; fakes `eval_fakes.py:110`, `test_llm_eval_document_level.py:138` keep their runtime behaviour (tests are not mypy-checked).

## TDD loop

### Red

Characterise first, against the current dict-based code, in `tests/test_payload_models.py` and in additions to the existing files; all green before any type changes.

1. **Mapper golden outputs.** `test_map_pvog_record_golden[live_shape_row]`, `...[v7_page_leaf_a]`, `test_map_govdata_record_golden[ozg_page_0]`, `...[open_pvog_live_shape_int_ozgid]`: assert the whole `CatalogueBatchItem.model_dump(mode="json")` against an inline expected dict, including `raw_payload == row` (and `_personal_matter_code` when given).
2. **Ladder order.** `test_pvog_title_ladder_prefers_title_then_name_then_leistungsname`, `test_govdata_title_ladder_order`, `test_description_ladders`, `test_steckbrief_label_prefers_title_then_titel_then_leistungsbezeichnung` (the last exists in `test_fim_steckbrief_label.py`; extend).
3. **Leniency.** `test_govdata_int_ozgid_becomes_external_id`, `test_pvog_blank_and_non_string_ids_are_skipped_in_the_dedupe_key`, `test_pvog_int_id_maps_but_is_not_a_dedupe_key` (pins the quirk), `test_steckbrief_non_string_title_is_ignored`, `test_non_dict_entries_in_content_are_dropped`.
4. **Page and bootstrap parsing.** `test_parse_v7_page_without_service_descriptions_is_last_and_empty`, `test_facades_leaf_codes_are_sorted_unique_and_stripped`, `test_last_flag_follows_truthiness_and_defaults_to_true`.
5. **Budget.** `test_iter_records_max_pages_zero_one_two_none` (guards the inlined `_budget_allows_fetch`).
6. **LLM JSON.** `test_build_json_schema_golden_for_a_small_taxonomy` (full dict, so the narrowing helper cannot change it), `test_prepare_schema_inlines_nested_and_sibling_refs`, `test_prepare_schema_refuses_a_recursive_ref_with_its_name`, `test_run_body_messages_are_plain_dicts`.
7. **Handlers.** `test_every_task_kind_has_a_handler_when_all_parts_exist` (equals `set(TASK_KINDS)`), `test_default_table_covers_worker_default_kinds`.

Negative path for the new code (fails first because the models do not exist):

- `test_pvog_page_with_non_object_body_raises_the_client_error` (A3's error type, not `ValueError`).
- `test_govdata_content_not_a_list_raises_value_error_with_the_existing_message`.
- `test_ckan_package_without_result_or_resources_raises_the_existing_messages`.
- `test_steckbrief_without_leistungsschluessel_raises_value_error`, `test_stammtext_without_ids_raises_value_error`.
- `test_steckbrief_from_body_returns_none_for_invalid_utf8_non_json_and_non_object` (three parametrised inputs, matching today's `_parse_steckbrief_body`).
- `test_fixture_key_mismatch_raises_fim_client_error`.
- `test_handler_table_rejects_unknown_kind_key` is a mypy check, not a pytest: the Verification step runs `mypy` and the PR lists the one-line probe used.

Run the narrow suite: the new model tests fail on import; the characterisation tests pass.

### Green

1. Add `json_types.py`, `lenient.py`, `catalogue_scope.py` with unit tests (`optional_str` and `text_or_none` tables: `None`, `""`, `"  "`, `" x "`, `0`, `7`, `True`, `[]`).
2. Add the three models modules; switch the clients, then the mappers, then `enrich.py` and `worker/enrich_metadata.py`, one source at a time with the narrow suite green after each.
3. Introduce `JsonSchema`, `ChatMessage`, `_resolve_object`/`_resolve_value`; switch the LLM files.
4. Key the handler table by `DiscoveryTaskKind`.
5. Remove the `ANN401` and `D` baseline entries for each rewritten file (T2 and T1 baselines).

### Refactor

Judge by responsibility, not line count: each model describes one wire shape and nothing else; clients fetch and parse; mappers map. Check for: leftover `isinstance` ladders (expected none), a model that grew behaviour beyond reading its own keys (move it to the mapper), duplicated lenient validators across the three models (rule of three: `lenient.py` owns them), any `# type: ignore` or `cast` that crept in (none allowed), `first_present` used wherever a ladder remained, and the `_resolve` pair still reading as one recursion. Every new public class, function and property has an imperative docstring that states intent without restating the signature (pydocstyle `D`, `pep257`); the files rewritten here also get their missing docstrings (D107 `__init__`, D401 imperative mood). Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with the `Any` table before and after, the number of `isinstance` calls in the touched modules before and after, and `ruff --select D,ANN401` counts for the touched files.

## Verification

```bash
cd apps/discovery-ingest
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
uv run pytest tests/test_payload_models.py tests/test_pvog_client.py tests/test_pvog_cli.py tests/test_pvog_harvest.py \
  tests/test_govdata_client.py tests/test_govdata_ckan.py tests/test_govdata_fetch.py tests/test_govdata_cli.py \
  tests/test_fim_leika_enrich.py tests/test_fim_steckbrief_label.py tests/test_enrich_metadata_worker.py \
  tests/test_extraction_schema.py tests/test_llm_schema_prep.py tests/test_llm_client.py tests/test_cli_worker_llm.py
uv run pytest
grep -rn "\bAny\b" discovery_ingest --include=*.py | wc -l      # 67 before, 2 after (capture_requeue.py, removed by I4)
cd ../..
./ci.sh
```

## Parallel notes

Siblings in the same batch: I1, B3, B4, W3, W4, and the T1 step 2 slices.

- **I1** rewrites the client import and call lines in `worker/enrich_metadata.py`, `cli.py`, `extract/llm/evaluation/command.py` and 30 other modules. I2 owns only the typing hunks named above in `cli.py` and `worker/enrich_metadata.py`; the hunks are disjoint, so the chief of staff rebases whichever lands second. I2 does not touch `api_client.py`, `client/`, `config.py`, or `extract/llm/evaluation/command.py`.
- **T1 step 2** edits docstrings in the same directories (`pvog`, `govdata`, `fim`, `leika`, `extract/llm`). If a slice is open, land it first or rebase over it; this chapter rewrites those files and writes their missing docstrings itself.
- **A3** (before I2) changed `pvog/client.py` and `govdata/ckan.py` (error wrapping) and `worker/llm_setup.py`; start from its merged state.
- **Must not be touched:** `apps/api/**`, `schemas.py` field types (I5 owns the contract comparison; `raw_payload` stays `dict[str, object]`), `config.py` (I3), `cli.py` beyond the listed hunks (I3 and I4), `capture_requeue.py` (I4), `.github/**`, `pyproject.toml`.
- Unblocks **I3**: the operations layer takes `Steckbrief`/`Stammtext`/`PvogRecord`/`GovDataRow` instead of dicts and replaces the two page-cap loops with `PageBudget`.
