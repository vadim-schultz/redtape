---
name: "Chapter B1 — Locale and i18n"
overview: "One i18n picker with an explicit fallback order, ResolvedLocale instead of loose locale + enabled pairs, one DEFAULT_ENABLED_LOCALES constant, and /locales + /translations moved out of routes.py into a typed locales feature."
todos:
  - id: characterize
    content: "Pin pick_i18n, locations picker, pick_title, resolve_locale, /locales and /translations behaviour"
    status: pending
  - id: one-picker
    content: "Single pick_i18n with explicit fallback; delete the locations copy; pick_title keeps its slug order via the same code"
    status: pending
  - id: resolved-locale
    content: "ResolvedLocale and DEFAULT_ENABLED_LOCALES replace Locales and the loose pairs and literals"
    status: pending
  - id: locales-feature
    content: "New locales feature with LocaleRead and TranslationBundle; routes.py keeps only /health"
    status: pending
isProject: false
---

# Chapter B1 — Locale and i18n

**Repo:** `redtape` · **Branch:** `refactor/locale-i18n` · **Status:** planned

**Depends on:** none (batch 1) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (D1, D2, D3, section 5 row `api/routes.py`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/{locale_resolution,i18n_resolution,routes}.py`, `api/shared/locale.py`, `api/features/{locations,taxonomy}`, `api/features/documents/document_read.py` (plus the additions listed under Parallel notes)

**Findings:** D1, D2, D3, T5 (`routes.py` rows)

## Goal

Locale picking has one algorithm and one fallback order that is visible in the signature. The locale carrier is `ResolvedLocale` everywhere below the controllers. The default locale set is declared once. `/api/v1/locales` and `/api/v1/translations` leave `routes.py`, return typed models and are tested. Public JSON and cache headers stay identical.

## Verified facts (read this before the loop)

| Claim in the audit | What the code says | Consequence |
| --- | --- | --- |
| D1: "different endpoints return different languages" | `features/locations/service.py:11-29` `_pick_i18n` is **line-for-line the same algorithm** as `i18n_resolution.pick_i18n` (locale, `de`, `en`, sorted enabled, any value). Only the docstring omits the last step. | Deleting the copy changes no behaviour. |
| D1: third copy `pick_title` is "en-first" | `features/suggestions/slugs.py:12` `pick_title` is en, de, sorted keys, **stripped**. It feeds `slugify(...)` in `suggestions/handlers.py:67` (`_document_identity`), `discovery/candidate_key.py:12` and `schema/discovery/candidates.py:42`. The result becomes `Document.slug` and the candidate dedup key. | It is **not a display picker**; it derives durable identifiers. Converging its order to locale/de/en (decision D3) would change slugs and orphan dedup keys. **Deviation from D3, to be called out in the PR:** keep the en, de order, but run it through the same code. |
| D2: `("de","en")` hard-coded in 4 places | `app/lifespan.py:28`, `middleware/locale.py:21`, `locale_resolution.py:52` (`{"de", "en"}` when none enabled), `shared/locale.py:10` (`_DEFAULT_ENABLED`). The fallback loops `("de", "en")` repeat in `i18n_resolution.py:16`, `locale_resolution.py:59` and `locations/service.py:21`. `routes.py:38` and `shared/locale.py:9` repeat `"de"` as the default code. | One constant module (below). |
| D2: `Locales` dataclass | `documents/document_read.py:30` `Locales(locale: str, enabled: set[str])` is `ResolvedLocale(code, enabled)` under other names. It is built at `documents/service.py:75` and `:223`. | Replace by `ResolvedLocale`. |
| D3: `routes.py` has no tests | Confirmed: no test references `list_locales` or `translations_bundle`. `resolve_locale` is only covered indirectly by `tests/test_controller_params_characterization.py:71`. | Characterise first. |

Wire shapes to keep: `GET /api/v1/locales` returns a JSON array of `{code, name_native, name_english, flag_emoji, enabled, completeness_pct}`; `GET /api/v1/translations` returns `{"locale": ..., "translations": {key: value}}` with `Cache-Control: public, max-age=3600, stale-while-revalidate=86400`. The web reads both (`apps/web/src/hooks/useLocalesQuery.ts`, `services/translationsApi.ts`).

## Files

| File | Change |
| --- | --- |
| `apps/api/app/shared/locale.py` | Add `DEFAULT_LOCALE = "de"`, `FALLBACK_ORDER: tuple[str, ...] = ("de", "en")`, `DEFAULT_ENABLED_LOCALES: frozenset[str]`. `provide_resolved_locale` uses them. No import from other `app` modules, so it cannot create a cycle. |
| `apps/api/app/i18n_resolution.py` | One `pick_i18n(values, locale: ResolvedLocale, *, fallback: Sequence[str] = FALLBACK_ORDER) -> str`. Chain: `locale.code`, then `fallback`, then sorted `locale.enabled`, then any non-blank value. Docstring states this order. |
| `apps/api/app/locale_resolution.py` | `resolve_locale` uses the constants instead of `{"de","en"}` and the literal loop. Add docstrings for `normalize_locale_tag`. Signature unchanged. |
| `apps/api/app/middleware/locale.py` | Replace `{"de", "en"}` at line 21 with `DEFAULT_ENABLED_LOCALES` (file is outside the touches table; no sibling touches it). |
| `apps/api/app/features/locations/service.py` | Delete `_pick_i18n`. Each `list_*` takes `locale: ResolvedLocale` (one param, was two). |
| `apps/api/app/features/locations/controller.py` | Pass `locale` through (it already receives `ResolvedLocale`). |
| `apps/api/app/features/taxonomy/service.py` | `list_domains`, `list_situations`, `list_situation_groups`, `list_situations_with_group`, `to_term_read`, `_list` take `ResolvedLocale`. |
| `apps/api/app/features/taxonomy/controller.py`, `app/features/candidates/service.py:72-73` | Callers pass `locale` instead of `locale.code, locale.enabled`. |
| `apps/api/app/features/candidates/localize.py` | Forward to the new `pick_i18n` signature (it already holds a `ResolvedLocale`). Check whether `localized()` is then a one-line wrapper with three or more callers; keep or inline by that test. |
| `apps/api/app/features/documents/document_read.py` | Delete `Locales`; every method takes `ResolvedLocale`. |
| `apps/api/app/features/documents/service.py` | **Two-line exception to the touches table:** lines 75 and 223 build `Locales(...)`; change to `ResolvedLocale(code=locale, enabled=enabled_locales)`. Signature conversion of this service is chapter B3's. |
| `apps/api/app/features/suggestions/slugs.py` | `pick_title` keeps its name, contract and docstring ("slug source, intentionally not display order") and delegates: `pick_i18n(title_i18n, ResolvedLocale(code="en", enabled=set(title_i18n)), fallback=("de",)).strip()`. Another sanctioned small edit; `slugify` is untouched. |
| `apps/api/app/routes.py` | Keep only `health`. |
| New `apps/api/app/features/locales/{__init__,repository,service,controller,dependencies,router}.py` | Same layout as `features/taxonomy`. Repository: `list_enabled()`, `translations_for(code)`. Service maps rows to models. Controller `LocalesController` with `GET /locales` (`list[LocaleRead]`) and `GET /translations` (`TranslationBundle`, `response_headers={"Cache-Control": ...}`); the translations handler takes `locale: ResolvedLocale`, not `request.state`. Router at `/api/v1`, tag `locales`. |
| New `apps/api/app/schema/locale/{__init__,read}.py` | `LocaleRead(code, name_native, name_english, flag_emoji: str \| None, enabled, completeness_pct)` with `from_attributes=True`; `TranslationBundle(locale: str, translations: dict[str, str])`. |
| `apps/api/app/main.py` | Register `locales_router`; drop `list_locales`, `translations_bundle` imports. |
| Tests to update | `tests/test_i18n_resolution.py` (4 tests, new signature), `tests/test_locations_repository.py:96-108`, `tests/test_taxonomy_service.py:26-55`, `tests/test_shared_paging_locale.py` (constants). |

**Not touched:** `app/lifespan.py` (chapter A4 owns it). It still contains the literal `{"de", "en"}` at line 28; B1 leaves it and records a one-line follow-up in the ledger: whoever merges second replaces it with `DEFAULT_ENABLED_LOCALES` (A4's TTL re-read will touch that line anyway).

## TDD loop

### Red

Characterise first, on `main`, all green:

1. `tests/test_i18n_resolution.py` extended: `test_pick_i18n_prefers_requested_then_de_then_en_then_sorted_enabled_then_any`, `test_pick_i18n_skips_blank_values`, `test_pick_i18n_returns_empty_for_none_and_for_all_blank`.
2. `tests/test_locale_resolution.py` (new): `test_query_locale_wins_over_accept_language`, `test_accept_language_picks_highest_q_among_enabled`, `test_unknown_tag_falls_back_de_then_en_then_first_enabled` (enabled `{"fr"}` returns `fr`), `test_empty_enabled_set_means_de_en`.
3. `tests/test_locations_picker_characterization.py` (new): feed the same `name_i18n` fixtures to `locations.service._pick_i18n` and `pick_i18n` and assert equal output (this proves the "identical copy" claim, then is deleted with the copy).
4. `tests/test_suggestion_slugs.py` already pins `pick_title` (en first, then de, then any). Add `test_pick_title_strips_and_skips_blank_en` and `test_pick_title_ignores_requested_locale_order` (keys `{"en": " ", "de": "Anmeldung"}` returns `Anmeldung`).
5. `tests/test_locales_api.py` (new, uses the `monkeypatch.setattr("app.main.provide_session", ...)` client pattern of `tests/test_controller_params_characterization.py`):
   - happy: `test_locales_lists_enabled_locales_sorted_by_code_with_all_fields` (seed two enabled, one disabled; the disabled one is absent; exact key set).
   - happy: `test_translations_returns_bundle_for_request_locale_with_cache_header` (assert the `Cache-Control` value verbatim and `locale` echo).
   - negative: `test_translations_for_unsupported_locale_falls_back_to_de` (`?locale=xx`).
   - negative: `test_translations_for_locale_without_rows_returns_empty_bundle`.

Then the new-behaviour red tests:

6. `test_pick_i18n_honours_explicit_fallback_order` (`fallback=("en","de")` picks `en` when the requested locale is missing) fails: no `fallback` parameter.
7. `test_default_enabled_locales_is_single_source` asserts `provide_resolved_locale`, `LocaleResolverMiddleware` and `resolve_locale` agree on `DEFAULT_ENABLED_LOCALES`; fails: constant missing.
8. `test_locale_read_rejects_missing_fields` and `test_translation_bundle_shape`: model tests; fail: models missing.

### Green

1. Add constants to `shared/locale.py`, switch `provide_resolved_locale`, `resolve_locale`, middleware.
2. Rewrite `pick_i18n` with the `ResolvedLocale` signature and explicit `fallback`; port its 4+ call sites (`document_read.py` x5, `taxonomy/service.py` x2, `candidates/localize.py`).
3. Delete `_pick_i18n` and the characterisation test of item 3; convert `locations` and `taxonomy` services to `ResolvedLocale`.
4. Delete `Locales`; fix the two `documents/service.py` lines.
5. Delegate `pick_title` to `pick_i18n`; the slug tests from item 4 prove the slugs did not move.
6. Create the `locales` feature and schema; move the two handlers; register the router; remove them from `routes.py` and `main.py`.

### Refactor

Gate: judge by responsibility, not line count. Check that `pick_i18n` is describable without "and"; that `LocationsService` no longer has five copies of the same `LocationNode` mapping loop only if a **fourth** identical arm exists (rule of three: count the arms in `list_countries`, `list_states`, `list_districts`, `list_cities`; they differ in `kind` and `administrative_role`, so extract only if one helper takes at most three parameters); that `candidates/localize.localized` is not now a pure one-line delegation; that no new `Any` appears (the removed `dict[str, Any]` from `routes.py` is the point); that every new public symbol has a docstring; and that the touched files' `D` and `ANN401` baseline entries are removed (`routes.py`, `i18n_resolution.py`, `locale_resolution.py`, `shared/locale.py`, `features/locales/*`). `app.middleware.locale` is in the mypy `ignore_errors` override (`pyproject.toml:86-92`, together with `features.locations.repository`); B1 edits that file, so run mypy on it with the entry temporarily removed locally, fix what shows, and leave the config edit itself to chapter G2 (config belongs to T2/G2). Record `Refactor gate: smells found -> ..., refactorings applied -> ...` in the PR, plus the `measure_code_rules.py` before and after numbers.

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_i18n_resolution.py tests/test_locale_resolution.py tests/test_locales_api.py \
  tests/test_suggestion_slugs.py tests/test_shared_paging_locale.py tests/test_locations_repository.py \
  tests/test_taxonomy_service.py tests/test_document_service.py tests/test_controller_params_characterization.py \
  tests/test_document_jurisdiction_path.py
cd ../..
./ci.sh
```

Also run `cd apps/web && npm test -- translationsApi useLocalesQuery` (read-only) to confirm the wire shape the web consumes is unchanged.

## Parallel notes

Runs alongside the other batch-1 chapters: A1, A2, A3, A4, B6, W1, W2, T1 step 1, T2, T3. Do not touch `apps/api/app/lifespan.py` (A4), `features/voting` and `features/suggestions/{controller,handlers,transitions}.py` (A1), `features/discovery/*` (A2), `services/openplz_client.py` and `scripts/` (B6), or any ruff/mypy config (T1, T2). The small edits to `documents/service.py` (two lines) and `suggestions/slugs.py` (`pick_title` body) are on files no batch-1 chapter owns; B2 (suggestions core) and B3 (documents) rebase onto them. B3 is `After: B1` and inherits the follow-up to convert `documents/service.py` signatures to `ResolvedLocale` and to decide where `pick_title` lives (its `schema/discovery/candidates.py` import is finding L5).
