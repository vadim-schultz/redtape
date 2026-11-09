---
name: "Chapter 2 — Backend locale foundation"
overview: "Make one list of supported locales drive seeds and validation, add tr, ru, uk, pl and ro as disabled locales, implement the new fallback chain, and compute locale completeness instead of hardcoding it."
id: C2
depends_on: []
touches:
  - apps/api/app/shared/locale.py
  - apps/api/app/locale_resolution.py
  - apps/api/app/i18n_resolution.py
  - apps/api/app/lifespan.py
  - apps/api/app/features/locales/
  - apps/api/app/schema/suggestion/payload.py
  - apps/api/app/schema/discovery/
  - apps/api/scripts/seed_i18n.py
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: single-list
    content: "Introduce SUPPORTED_LOCALES as the one code list driving seed rows and JSONB key validation."
    status: pending
  - id: new-locales
    content: "Seed tr, ru, uk, pl and ro as disabled locales without overwriting an operator's enabled flag."
    status: pending
  - id: fallback
    content: "Implement the per-locale fallback chain (requested, en, de for non-German readers)."
    status: pending
  - id: completeness
    content: "Compute completeness_pct from ui_translation coverage."
    status: pending
  - id: tests
    content: "Add resolution, validation, fallback, seed and completeness tests."
    status: pending
---

# Chapter 2 — Backend locale foundation

**Repo:** `redtape` (`apps/api`)
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Today the locale list is hardcoded in three places (`scripts/seed_i18n.py`, `app/shared/locale.py` `FALLBACK_ORDER`, and the web fallback map), JSONB locale keys are validated by a loose regex only, and `completeness_pct` is always 100. Make the backend ready to carry seven locales safely, with the new ones switched off.

## Design decisions

- `SUPPORTED_LOCALES` in `app/shared/locale.py` is a typed constant (code, native name, English name, flag) for `de en tr ru uk pl ro`. It seeds `supported_locale` and validates locale keys. The `enabled` column decides serving.
- `seed_i18n.seed_supported_locales` inserts missing locales with `enabled=false` (existing `de` and `en` stay enabled) and on conflict updates names only, never `enabled`. An operator's flip persists across deploys (`start.sh` runs the seed on every boot).
- `seed_ui_translations` globs `scripts/seed_data/translations/*.json` as today; a file for a locale that is not in `SUPPORTED_LOCALES` is an error, not a silent skip.
- Replace the regex-only key check in `schema/suggestion/payload.py` (`^[a-zA-Z]{2,5}$`) and the looser discovery schemas (`schema/discovery/candidates.py`, `machine.py`, `candidate_emit.py`) with a shared validator over `SUPPORTED_LOCALES`. Keys are lowercased as today; unknown codes are rejected with a message naming the key.
- Fallback (decision D5) becomes a function `fallback_chain(locale) -> tuple[str, ...]`: German readers `de → en`; others `requested → en → de`. `pick_i18n` (`app/i18n_resolution.py`) uses it; its existing last resorts (any enabled locale, any non-blank value) stay. `FALLBACK_ORDER` is removed. The slug call that passes `fallback=("de",)` (`features/suggestions/slugs.py`) keeps its explicit behaviour.
- `completeness_pct` is computed from `ui_translation`: keys present for the locale divided by keys present for `de`, rounded, returned by `GET /locales`. No stored value, no migration.
- `normalize_locale_tag` and `parse_accept_language` already handle two-letter primary subtags, which all seven codes are; tests pin that.
- Locale resolution and the enabled-set refresh in `app/lifespan.py` are unchanged: a disabled locale is never in `enabled_locale_codes`.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/shared/locale.py` | `SUPPORTED_LOCALES`, `fallback_chain`; remove `FALLBACK_ORDER`. |
| `apps/api/app/i18n_resolution.py` | Use `fallback_chain`. |
| `apps/api/app/schema/suggestion/payload.py` | Shared locale-key validator. |
| `apps/api/app/schema/discovery/candidates.py`, `machine.py`, `candidate_emit.py` | Use the same validator. |
| `apps/api/app/features/locales/` | Computed `completeness_pct` in the locales read. |
| `apps/api/scripts/seed_i18n.py` | Seed all supported locales, `enabled=false` for new ones, never overwrite `enabled`. |
| `apps/api/tests/test_locale_resolution.py` | New tags, region subtags, unsupported and disabled locales. |
| `apps/api/tests/test_i18n_resolution.py` | Fallback chain per locale. |
| `apps/api/tests/test_seed_i18n.py` | Seed behaviour, enabled flag preserved, unknown locale file rejected. |
| `apps/api/tests/test_suggestion_payload.py` | Key validation. |
| `apps/api/tests/test_locales_api.py` | Computed completeness; only enabled locales listed. |

## Red tests

### Happy path

- `resolution · tr, ru, uk, pl, ro resolve when enabled` asserts `?locale=` and `Accept-Language` pick each code, and `de-AT` resolves to `de`.
- `fallback · a Turkish reader gets en before de` asserts a value present in `en` and `de` resolves to `en`; a value only in `de` resolves to `de`.
- `seed · adds the new locales disabled and keeps an enabled flag flipped by an operator`.
- `locales api · completeness is computed` asserts 100 for `de`, a partial percentage for a locale with half the keys.

### Negative path

- `resolution · a disabled locale is never served` asserts `?locale=tr` falls back to the default while `tr` is disabled.
- `payload · an unsupported locale key is rejected` asserts `fr` and malformed keys fail with a message naming the key.
- `seed · a translation file for an unknown locale fails loudly`.
- `fallback · German readers still get de before en`.

## Green

1. Add `SUPPORTED_LOCALES` and `fallback_chain`; migrate `pick_i18n`.
2. Update the seed; add the locale rows.
3. Replace key validators.
4. Compute completeness.

## Refactor gate

- No second locale list remains in `apps/api` (`grep` for `"de", "en"` tuples and `FALLBACK_ORDER`).
- One validator, shared by all schemas, no copy per schema.
- `pick_i18n` keeps one ordering rule; callers do not re-implement fallback.
- Docstrings and types on the new constants and functions; no `Any`.

## Verification

```bash
cd apps/api
uv run pytest tests/test_locale_resolution.py tests/test_i18n_resolution.py \
  tests/test_seed_i18n.py tests/test_suggestion_payload.py tests/test_locales_api.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../.. && ./ci.sh
```

Record the seeded locale rows and the computed completeness values in [../run-ledger.md](../run-ledger.md).

## Out of scope

Web changes, translating any strings (chapter 11), enabling a locale, document translation (chapters 13 to 15), right-to-left support.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/search-backend-locales
```

```text
test(api): describe supported locales, fallback chain and seed
feat(api): drive locale seeds and validation from one list
```
