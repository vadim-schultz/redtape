---
name: "Chapter 04 — Interface-string translation on Azure"
overview: "Let i18n translate-ui fill missing interface keys with the Azure engine. Keys added to German become translated without the Cloudflare LLM. The run is additive only, and plural forms come out right for ru, uk, pl, tr and ro, where MT would otherwise drop the inflection note."
id: AZ04
depends_on:
  - AZ02
  - AZ03
touches:
  - apps/discovery-ingest/discovery_ingest/i18n/
  - apps/discovery-ingest/discovery_ingest/operations/translate_ui.py
  - apps/discovery-ingest/discovery_ingest/translation/tokens.py
  - apps/discovery-ingest/tests/
  - apps/api/scripts/seed_data/translations/
  - apps/web/src/i18n/fallback/
execution: chapter-implementer
---

# Chapter 04 — Interface-string translation on Azure

**Repo:** `redtape` (`apps/discovery-ingest`, seed data, web mirrors) · **Depends on:** [Chapter 02](02-azure-engine-adapter.md), [Chapter 03](03-character-meter-and-floor.md) · **Decisions:** [D4](../gaps-and-decisions.md#d4--interface-locales-are-enabled-on-machine-output) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

`i18n translate-ui` can run on `azure-translator`. It fills only the keys a locale does not have yet. Plural categories are generated from representative numbers, because MT receives no inflection context. Placeholders survive translation byte-for-byte.

## Scope

- In: representative-number plural expansion for MT, placeholder protection, a `translate-ui` run on Azure, additive-only tests.
- Out: enabling locales and review status (chapter 14), the glossary gate (chapter 05), new German keys (none are added by this suite; the five bundles are already complete).

## Design

1. **Why plurals need work.** `plural.py` expands a German `other` form into each category. The inflection note travels in `TranslationUnit.context`, and MT drops it. Russian `one`, `few`, `many` and `other` would all come back as the same German text.
2. **Representative numbers.** For each locale and plural category, a CLDR sample number is substituted for `{count}` in the German text. Each category is translated as one unit. The sample digits are then replaced back with `{count}`. A sample is used only if the source does not already contain it, so a sample is never confused with a placeholder or a real number.
3. **Placeholders.** `{name}` tokens are protected with `translation/tokens.py` before the call and restored after it. A missing or changed placeholder is a validation failure.
4. **Additive only.** `translate_locale` already skips keys that exist. `LocaleRun.__init__` prunes keys that are not in `required`. Both rules are pinned by tests, and human-corrected values of keys still in German are never sent or overwritten.
5. **Failures.** `repairs` is `False` for Azure, so a failing string is reported in the run summary and not re-asked.
6. **Module.** The expansion lives in `i18n/plural_mt.py`, so `plural.py` keeps its current behaviour for the other engines.

## Files

| Path | Change |
| --- | --- |
| `i18n/plural_mt.py` (new) | representative numbers and expansion, restoration |
| `i18n/batch.py`, `i18n/translate_ui.py` | route MT plurals through `plural_mt`; keep additive behaviour |
| `operations/translate_ui.py` | Azure meter wiring already from chapter 03; summary per locale |
| `translation/tokens.py` | placeholder token tests |
| `tests/test_i18n_*.py`, `tests/test_plural_mt.py` (new) | pure and flow tests |

## Red tests

**Happy path**
- `Plural · a Russian one/few/many/other key yields four distinct translations from four representative numbers`
- `Plural · the sample number is not one already present in the source`
- `Placeholders · {name} survives translation byte-for-byte`
- `Additive · a run leaves existing keys untouched and fills only the missing ones`
- `Run · translate-ui on azure-translator writes the seed and mirror files and reports per-locale counts`
- `Prune · human-corrected ru plurals survive a run`

**Negative path**
- `Plural · identical forms for few and many in ru are rejected by the existing family validator`
- `Placeholders · a missing placeholder in the output is a validation failure`
- `Run · a string that fails validation is reported once; the engine is called exactly once for it`
- `Run · a quota stop writes no partial file`

## Green

Implement each red test in order. Keep `plural.py` unchanged for the `llm` engine; the existing plural tests are the guard.

## Refactor gate

- `plural_mt.py` has one job: choose sample numbers, build texts, restore counts. Split into small functions of about 5 lines each.
- Sample numbers come from a table keyed by locale and category, not from an if-chain per locale.
- Rule of three applies to the placeholder protect and restore pair, if a third caller appears.
- House rules: about 100 lines per file, at most 3 parameters, no boolean flags.

## Verification

```bash
cd apps/discovery-ingest
.venv/bin/python -m pytest -q tests/test_i18n_*.py tests/test_plural_mt.py tests/test_translation_context.py tests/test_i18n_committed_locales.py tests/test_i18n_manifest.py
cd ../api && .venv/bin/python -m pytest -q tests/test_seed_i18n.py
cd ../web && npm test -- fallback parity
cd ../.. && ./ci.sh
```

## Out of scope

Enabling locales, review status and `machine_accepted` (14), the glossary gate (05), new keys in German, right-to-left handling.

## Operator steps after merge

None for this chapter. The five existing bundles already have complete keys, so a run is needed only when a later chapter adds keys.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-04-ui-strings
# test(ingest): ... (red), feat(ingest): ... (green), refactor(ingest): ... (gate)
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
