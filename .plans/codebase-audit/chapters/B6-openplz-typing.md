---
name: "Chapter B6 — OpenPLZ typing"
overview: "The OpenPLZ client returns typed models per endpoint instead of Any, moves out of app/services to the locations feature, the stable-UUID rules live in one module, and the one-shot Saxony repair leaves start.sh once an operator confirms it ran."
todos:
  - id: characterize
    content: "Pin the importer against the typed fake, the paged payload shapes and the stable UUIDs"
    status: pending
  - id: typed-client
    content: "Typed endpoint methods and one paged parse; no Any; move next to its models"
    status: pending
  - id: shared-ids
    content: "scripts/openplz_ids.py replaces the two copies of UUID_NAMESPACE and _stable_uuid"
    status: pending
  - id: saxony
    content: "Retire fix_saxony_jurisdiction_leak from start.sh (operator confirmed 2026-11-02) and add the dry-run-first cleanup for the leaked Kreis Beispiel and Musterstadt rows (C8)"
    status: pending
isProject: false
---

# Chapter B6 — OpenPLZ typing

**Repo:** `redtape` · **Branch:** `refactor/openplz-typing` · **Status:** planned

**Depends on:** none (batch 1) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (D15, T5 row `openplz_client.py`, section 5) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/services/openplz_client.py`, `api/scripts/` (plus the new locations-feature modules and `app/schema/openplz.py` listed under Files)

**Findings:** D15, T5 (`openplz_client.py`), misplaced `openplz_client`

## Goal

`OpenPLZClient` has no `Any` and no `Callable[[Any], T]`: each endpoint returns validated models. The client and its models sit with the feature that owns the data, not in a generic `app/services`. The deterministic UUID rules exist once. Re-running the import produces byte-identical ids and rows. The importer's command line (`python scripts/import_openplz_locations.py --language de [--dry-run] [--commit-every N] [--states 14]`, called by `.github/workflows/platform-maintenance.yml:59` and documented in `docs/operations/openplz-import.md`) is unchanged.

## Verified facts

| Claim | What the code says |
| --- | --- |
| 11 `Any` in `openplz_client.py` | Confirmed and slightly understated: `Any` appears on 12 lines (19 occurrences): imported at line 9; `params: dict[str, Any]` (64, 95, 140, 153), `_parse_json -> Any` (92), `get_json -> Any` (95), `payload: Any` (100, 128, 131), `list[Any]` returns (100, 111, 114, 128, 131), `Callable[[Any], TParsed]` (143). |
| Typed models do not exist | **They already do**: `app/schema/openplz.py` defines `OpenPLZFederalState`, `OpenPLZDistrict`, `OpenPLZMunicipality`, `OpenPLZLocality` (and their `*Ref` types) with `extra="ignore"` and camelCase aliases. The importer validates each raw item itself (`import_openplz_locations.py:249,285,317,347`). The audit's "one model per endpoint" is therefore about moving the validation *into* the client, not writing new DTOs. |
| `item_parser` / `get_json` | `iter_paged(item_parser=...)` is never passed by the importer; `get_json` is called once, for `FederalStates` (`:248`). |
| Consumer | `OpenPLZClient` is imported only by `scripts/import_openplz_locations.py:17`; `app/schema/openplz.py` is imported only by the same script. Test double: `tests/test_import_openplz_incremental.py:62-76` (`_FakeClient` replaces `importer.OpenPLZClient`; it implements `get_json` and `iter_paged`). |
| Duplicate ids | `UUID_NAMESPACE` and `_stable_uuid` are defined in `import_openplz_locations.py:25-30` and `cleanup_openplz_data.py:15,22-24`. The key formats are spelled out six times in the importer (`:224,260,289,321,357,359`) and again in `cleanup_openplz_data.py:39-43,75`. A typo in one place orphans rows silently. `tests/test_import_transforms.py:1` imports `_stable_uuid` from the importer. |
| mypy | `pyproject.toml:85-92`: `app.services.openplz_client` (and `app.middleware.locale`, `app.features.locations.repository`, `app.features.documents.service`) are `ignore_errors = true`; `scripts.*` is `ignore_errors = true` (`:81-83`). |
| `start.sh` | `scripts/start.sh:14` runs `python -m scripts.fix_saxony_jurisdiction_leak` on every boot, before `seed_jurisdictions`; comments at lines 6-8 and 12-13 explain it. The script prints `no-op, nothing to repair` once its trigger row (id `11111111-1111-1111-1111-111111111103` with code `14612000`) is gone (`fix_saxony_jurisdiction_leak.py:49-53,119-122`). Its test is `tests/test_fix_saxony_jurisdiction_leak.py`. |

## Design

1. **Where the client goes, and why not `scripts/`.** The audit says "next to the consumer", which is `scripts/`. But `scripts.*` is exempt from mypy, so a typed client there would not be checked. Move it instead to `apps/api/app/features/locations/openplz/` (`client.py`, `models.py` from `app/schema/openplz.py`, `__init__.py`), which `uv run mypy app scripts` checks in full because the module path is not in any override. `app/services/` and `app/schema/openplz.py` disappear. The stale override entry `app.services.openplz_client` in `pyproject.toml` is left for chapter G2 (config belongs to T1/T2/G2; B6 must not edit `pyproject.toml`). If the implementer prefers `scripts/openplz/`, T2 must first narrow the `scripts.*` override; do not do both.
2. **Typed client.** Endpoint methods instead of `endpoint: str`:
   - `federal_states() -> list[OpenPLZFederalState]`
   - `districts(state_code) -> Iterator[OpenPLZDistrict]`
   - `municipalities(district_code) -> Iterator[OpenPLZMunicipality]`
   - `localities(district_code) -> Iterator[OpenPLZLocality]`
   all over one private `_paged(endpoint, model: type[ModelT], page_size) -> Iterator[ModelT]` with `ModelT = TypeVar(bound=BaseModel)`, and one `_get_json(endpoint, params: Mapping[str, str | int]) -> JsonValue` (`pydantic.JsonValue`, the recursive alias from audit section 5). The three `_handle_paged_*` methods plus `_select_paged_payload_handler` and `_extract_paged_items` collapse into one validation of "a list, or an object with `items`, else `data`" via a small generic `_PagedEnvelope(BaseModel, Generic[ModelT])` and `TypeAdapter`. Behaviour kept exactly: a list is the page; an object uses `items`, else `data`; an empty page ends iteration; `max_pages` still stops. A malformed page raises `OpenPLZPayloadError(RuntimeError)` carrying the endpoint and page (it replaces the two bare `RuntimeError`s; nothing catches `RuntimeError` today: `import_openplz_locations.py` only catches `IntegrityError`). `item_parser` and public `get_json` are removed (no callers). `urllib`, the rate limiter and `OpenPLZHTTPError` stay.
3. **Importer.** Replace the four `model_validate` loops by the typed calls. `_import_states` iterates `self._client.federal_states()`. Behaviour of `or []` for an empty state list stays (an empty list parses to an empty list).
4. **Shared ids.** New `scripts/openplz_ids.py` (sits with `openplz_rows.py` and `openplz_writes.py`): `UUID_NAMESPACE`, `stable_uuid(key)`, and one function per key format: `country_id(code)`, `region_id(code)` (states and districts share it, as today), `municipality_id(code)`, `locality_id(municipality_code, postal_code, name)`. `cleanup_openplz_data._expected_jurisdiction_id` maps `JurisdictionKind` to these functions. **The key strings must not change** because the ids are persisted: the golden values below pin them.
5. **Saxony repair (approved).** Remove `python -m scripts.fix_saxony_jurisdiction_leak` and its comments from `scripts/start.sh` only after the confirmation below. Do not delete the script or its test in this chapter (a later cleanup can; `.plans/document-browse-confidence/chapters/08-remove-seeded-documents.md` and `gaps-and-decisions.md:22` reference it). The operator confirmed on 2026-11-02, so remove the call.
6. **Leaked fixture rows (C8).** Read-only first: look up the two rows by `(kind, code)` (`district`/`146`, `municipality`/`14612`) and list everything that references them (`Document`, `DocumentRequirement`, `Suggestion`, `Locality`; the four tables in `_JURISDICTION_REFERENCES`). Then add `scripts/remove_leaked_fixture_jurisdictions.py`: dry-run by default, `--apply` required to write, idempotent, repoints or refuses when anything real references the rows, with a test written red first against a seeded copy of the leak. The operator runs it with `--apply` against production; the chapter's agent never touches production. Add C8 to the ledger as done only after the operator reports the `GET /districts?state=14` result with 13 districts.

### Operator confirmation and live evidence (2026-11-02)

The operator confirmed that the Saxony repair has been run and repaired the data, so removing the call from `start.sh` is approved. A read-only check against the public API on `https://redtape.cc/api/v1` agrees on the main point:

- `GET /states?country=DE` returns 16 states including `14 Sachsen`.
- `GET /districts?state=14` returns 14 districts: the 13 real ones (Chemnitz, Erzgebirgskreis, Mittelsachsen, Vogtlandkreis, Zwickau, `14612 Dresden, Stadt`, Bautzen, Görlitz, Meißen, Sächsische Schweiz-Osterzgebirge, `14713 Leipzig, Stadt`, Leipzig, Nordsachsen).
- `GET /cities?district=14612` returns `14612000 Dresden, Stadt`, which is the real municipality code the repair keys on.

**New finding C8 (not caught by the repair):** the same endpoints still return two test-fixture rows. `GET /districts?state=14` contains `146 · Kreis Beispiel`, and `GET /cities?district=146` contains `14612 · Musterstadt`. Those names are the fixtures in `tests/test_fix_saxony_jurisdiction_leak.py:35,44` and `tests/test_locations_repository.py:60,72`, and `scripts/fix_saxony_jurisdiction_leak.py` names them as leaked. A scan of the other 15 states found no further fixture-looking rows. The public API cannot tell whether these rows carry the ids in `LEAKED_DISTRICT_ID` and `LEAKED_MUNICIPALITY_ID`, so step 6 below starts with a read-only lookup.

### How to confirm the Saxony repair was applied (optional now, read-only)

The operator's confirmation and the live evidence above are enough to proceed. The queries below remain a cheap double check for whoever has database access.

1. In the production database, run `SELECT id, code FROM jurisdiction WHERE id IN ('11111111-1111-1111-1111-111111111103','c3d315b5-83da-5412-9119-4d9680d87fdb','732ab821-227b-5e04-a94e-329b1849a9a9');` It must return **zero rows** (these are `FAKE_DRESDEN_ID`, `LEAKED_DISTRICT_ID`, `LEAKED_MUNICIPALITY_ID`).
2. In the host's boot logs for the last three deploys, find `fix_saxony_jurisdiction_leak: no-op, nothing to repair` (and `fake Dresden lookup -> found=False`). A `repaired` line means it ran once more; wait for the next boot.
3. Check the same on staging, if one exists.
4. Only then remove the line from `start.sh`; the next boot still ends with `seed_jurisdictions`. The agent cannot do steps 1-3 (no production access): request them from the operator and wait for a written yes.

## Files

- Move `apps/api/app/services/openplz_client.py` to `apps/api/app/features/locations/openplz/client.py`; move `apps/api/app/schema/openplz.py` to `.../openplz/models.py` (use `git mv`); delete `app/services/__init__.py` if nothing else lives there (it only holds `openplz_client.py` today).
- `apps/api/scripts/import_openplz_locations.py` (imports, typed calls, ids), `scripts/cleanup_openplz_data.py` (ids), new `scripts/openplz_ids.py`.
- `apps/api/scripts/start.sh` (last, after confirmation); `apps/api/scripts/fix_saxony_jurisdiction_leak.py` untouched.
- Tests: `tests/test_import_openplz_incremental.py` (`_FakeClient` now implements the four typed methods by validating its dict dataset with the same models, so the dataset and every incremental-import assertion stay as they are), `tests/test_import_transforms.py:1` (import `stable_uuid` from `scripts.openplz_ids`), new `tests/test_openplz_client.py`, new `tests/test_openplz_ids.py`.
- Docs that name the old paths: none (`grep` of `docs/`, `.github/`, `README.md` finds no reference to `openplz_client`, `app/services` or `schema/openplz`).

## TDD loop

### Red

Characterise first (green on the unchanged code):

1. `tests/test_openplz_ids.py` golden values, computed from the current formulas at planning time: namespace `1221acf1-efe2-5dbc-8e6f-729112b021e5`; `country_id("DE")` is `e0273f59-194b-56b6-9a18-e2a7e1632413`; `region_id("14")` is `ddac3643-9ecf-5a51-b273-d881bff977dd`; `municipality_id("14612000")` is `4620006e-4e41-5403-aa9d-268e59dd916d`; `locality_id("14612000", "01067", "Dresden")` is `d9982633-c853-5a00-8f93-ecc5ed7309d2`. Add `test_ids_are_deterministic_across_calls`, `test_state_and_district_share_the_region_namespace`, and the negative `test_different_keys_give_different_ids`. Re-verify the literals on `main` before relying on them.
2. `tests/test_openplz_client.py` (no network: patch `OpenPLZClient._fetch_text` or serve a local `http.server`): `test_paged_list_payload_yields_models`, `test_paged_items_envelope_yields_models`, `test_paged_data_envelope_is_the_fallback`, `test_empty_page_stops_iteration`, `test_max_pages_stops_iteration`, `test_rate_limiter_rejects_non_positive_rps`, `test_http_error_carries_status_url_and_truncated_body`. Negative: `test_unexpected_payload_type_raises_payload_error_with_endpoint` and `test_item_missing_required_key_raises_payload_error` (both red-then-changed: today they raise a bare `RuntimeError` or a `ValidationError` in the importer; pin the new error class and message fields).
3. The existing 13 tests of `tests/test_import_openplz_incremental.py`, plus `test_import_openplz_locations.py` and `test_cleanup_openplz_data.py` stay green throughout.

Red for new shape: `test_client_has_no_any_in_its_public_signatures` (inspect `client.py` annotations: no `typing.Any`), `test_importer_uses_typed_endpoint_methods` (the rewritten `_FakeClient` has no `get_json`/`iter_paged`; the importer must not call them).

### Green

1. Add `scripts/openplz_ids.py`; switch importer and cleanup; delete the two private copies.
2. `git mv` the client and models; write the typed methods; switch the importer; update the fake.
3. Run the whole OpenPLZ test group, then mypy without any override for the moved path.
4. After confirmation only: edit `start.sh`.

### Refactor

Gate: judge by responsibility, not line count. The client should be describable as "fetch and validate OpenPLZ pages" (HTTP transport, rate limiting and parsing together are one responsibility here; split transport from parsing only if a second consumer appears). Do not extract a method to shorten `_import_districts_for_state` and its siblings: they are linear and share a loop shape of exactly three levels (states, districts, municipalities) so the rule of three does not yet call for a generic walker. Check no one-line wrapper is left (`_parse_json` is one: inline it). No new `Any`; docstrings (imperative mood) on the new public client methods, `OpenPLZPayloadError` and every function in `openplz_ids.py`; remove the `D` and `ANN401` baseline entries for the files rewritten. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with `Any` counts for the client before (12 lines, 19 occurrences) and after (0).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_openplz_client.py tests/test_openplz_ids.py tests/test_import_openplz_incremental.py \
  tests/test_import_openplz_locations.py tests/test_import_transforms.py tests/test_cleanup_openplz_data.py \
  tests/test_fix_saxony_jurisdiction_leak.py tests/test_locations_repository.py
python -c "import scripts.import_openplz_locations"      # still importable the way the workflow runs it
cd ../..
./ci.sh
```

Smoke check of the unchanged entry point (no network needed): `cd apps/api && python scripts/import_openplz_locations.py --help` prints the same options.

## Parallel notes

Runs in batch 1 alongside A1, A2, A3, A4, B1, W1, W2, T1 step 1, T2 and T3. Do not edit `pyproject.toml` or any ruff/mypy config (T1, T2; the stale `app.services.openplz_client` override is G2's to remove), `app/lifespan.py` (A4), `features/locations/service.py`, `controller.py` and `features/taxonomy` (B1; this chapter adds only a new subpackage `features/locations/openplz/` and does not edit existing files of that feature), `features/discovery`, `features/suggestions` or `features/voting`. `scripts/seed_*.py` and `scripts/start.sh` lines other than the Saxony step are not touched. `scripts/` receives docstring-only edits from T1 step 2 later: schedule that after this chapter.
