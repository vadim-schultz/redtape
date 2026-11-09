---
name: "Chapter 11 — UI and taxonomy-label translation"
overview: "Translate the interface strings and taxonomy labels into tr, ru, uk, pl and ro with an LLM on Workers AI, validate them mechanically, and keep each locale disabled until a native-speaker review is recorded."
id: C11
depends_on:
  - C2
  - C7
  - C10
touches:
  - apps/discovery-ingest/discovery_ingest/i18n/
  - apps/discovery-ingest/discovery_ingest/cli/i18n/
  - apps/discovery-ingest/tests/
  - apps/api/scripts/seed_data/translations/
  - apps/api/scripts/seed_data/taxonomy_translations.py
  - apps/api/scripts/seed_taxonomy.py
  - apps/api/scripts/seed_i18n.py
  - apps/api/scripts/enable_locale.py
  - apps/web/src/i18n/fallback/
  - docs/operations/
execution: chapter-implementer
todos:
  - id: translator
    content: "Add the translate-ui command using the existing LlmClient, NeuronMeter and a glossary."
    status: pending
  - id: validators
    content: "Validate placeholders, plural forms, markup and length; repair or reject."
    status: pending
  - id: files
    content: "Generate the five locale files and a review manifest, and mirror them into the web bundles."
    status: pending
  - id: taxonomy
    content: "Translate category names and descriptions into a separate seed module merged by seed_taxonomy."
    status: pending
  - id: enable-guard
    content: "Add an enable_locale guard that refuses without a recorded review and full coverage."
    status: pending
  - id: tests
    content: "Add validator, manifest, seed, enable-guard and parity tests."
    status: pending
---

# Chapter 11 — UI and taxonomy-label translation

**Repo:** `redtape` (`apps/discovery-ingest`, `apps/api/scripts`, `apps/web`)
**Depends on:** [Chapter 2](02-backend-locale-foundation.md), [Chapter 7](07-web-locale-foundation.md), [Chapter 10](10-results-presentation.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Produce complete, mechanically valid translations of the interface into Turkish, Russian, Ukrainian, Polish and Romanian, ready for human review. It runs after the last UI copy change (chapters 9 and 10) so no key changes afterwards. **Documents are not translated here.**

## Design decisions

- **Command.** `python -m discovery_ingest i18n translate-ui --locale <code>` (new `discovery_ingest/i18n/` module and `cli/i18n/`). It reads the `en` and `de` seed files (`apps/api/scripts/seed_data/translations/`), and translates through the existing `LlmClient` and `NeuronMeter` (`extract/llm/`), batches of about 40 keys, JSON-schema output, using both `en` and `de` as sources plus the key path as context. It is resumable (skips keys already present) so later copy changes only translate the delta.
- **Glossary** (`i18n/glossary.py` or a data file): fixed renderings for domain terms (for example *Antrag*, *Bürgeramt*, *Nachweis*, the category names) per locale, injected into every prompt and checked after generation.
- **Validators** (`i18n/validate.py`), each a small pure function: the placeholder set equals the source's; the plural family has every category `Intl.PluralRules` requires for the locale (the command expands `key_one` and `key_other` into the target's forms, for example Russian `one/few/many/other`); no HTML or markdown introduced; length within a sane ratio of the source (flags text that would break layouts); no untranslated copies of the English source unless allow-listed (brand names, codes). Failures trigger one repair request, then are reported and left absent rather than written wrong.
- **Output.** `scripts/seed_data/translations/{tr,ru,uk,pl,ro}.json` (same nested structure as `en.json`), the same files mirrored into `apps/web/src/i18n/fallback/` (the existing parity test ties the two copies), and `scripts/seed_data/translations/review.json`: per locale `status` (`machine` or `reviewed`), `reviewed_by`, `reviewed_on`, model, command version.
- **Taxonomy labels (D8).** `scripts/seed_data/taxonomy_translations.py` maps category code → `{locale: (name, description)}`; `seed_taxonomy.py` merges it into `name_i18n` / `description_i18n`. The frozen `category_contract_v1.json` is not edited. The same translator and validators produce it. Existing `pick_i18n` serves the right label with the chapter 2 fallback chain.
- **Enabling is a guarded, explicit step.** `scripts/enable_locale.py <code>` sets `supported_locale.enabled = true` only if the manifest says `reviewed` and the computed completeness is 100; otherwise it refuses with the reason. Seeds never flip `enabled` (chapter 2).
- **Cost.** A few thousand short strings once; charged to the shared neuron ledger through `NeuronMeter` and recorded in the ledger file. Quota stops end the run cleanly and a re-run continues.
- **Not in scope but tempting:** machine translation of candidate titles or excerpts, a human review UI, right-to-left support.

## Files

| Path | Change |
| --- | --- |
| `apps/discovery-ingest/discovery_ingest/i18n/translate.py`, `glossary.py`, `validate.py`, `manifest.py` | Translator, glossary, validators, manifest. |
| `apps/discovery-ingest/discovery_ingest/cli/i18n/` | `translate-ui` command, registered in `cli/main.py`. |
| `apps/api/scripts/seed_data/translations/{tr,ru,uk,pl,ro}.json`, `review.json` | Generated data and manifest. |
| `apps/api/scripts/seed_data/taxonomy_translations.py`, `seed_taxonomy.py` | Taxonomy label translations and merge. |
| `apps/api/scripts/seed_i18n.py` | Read the manifest; no `enabled` changes. |
| `apps/api/scripts/enable_locale.py` | Guarded enable. |
| `apps/web/src/i18n/fallback/{tr,ru,uk,pl,ro}.json` | Mirrored bundles (lazy-loaded by chapter 7). |
| `apps/discovery-ingest/tests/test_i18n_validate.py`, `test_i18n_translate.py` | Validator and flow tests with a fake LLM. |
| `apps/api/tests/test_enable_locale.py`, `test_seed_taxonomy.py` | Guard and taxonomy merge. |
| `docs/operations/` (new `locales.md`) | How to translate, review and enable a locale. |

## Red tests

### Happy path

- `validate · accepts a translation with identical placeholders and complete plural forms`.
- `translate · expands one/other source keys into the target locale's plural categories` (Russian, Polish, Romanian, Turkish).
- `translate · resumes: existing keys are skipped and only the delta is requested`.
- `seed · loads all five files; completeness is computed as 100 for a complete locale`.
- `taxonomy · category names resolve to the new locale and fall back per D5 when missing`.
- `enable_locale · enables a reviewed, complete locale`.

### Negative path

- `validate · rejects a dropped or renamed placeholder, added markup, or a missing plural form` and one repair is attempted before the key is reported.
- `validate · flags an untranslated copy of the English source`.
- `enable_locale · refuses a machine-only or incomplete locale` with a reason.
- `translate · stops cleanly on quota exhaustion and writes nothing partial per batch`.
- `web parity · a locale file with a missing key or placeholder fails the suite`.
- `glossary · a glossary term rendered differently in the output is flagged`.

## Green

1. Validators and the manifest against fixtures.
2. Translator with a fake LLM, then one real run per locale (operator machine with the Workers AI token).
3. Taxonomy translations and the guarded enable script.
4. Mirror the web bundles; run parity.

## Refactor gate

- Validators are separate pure functions; the translator orchestrates them.
- No `Any`, no boolean flags, at most 3 parameters (use DTOs for batch and result).
- Glossary and manifest are data, not logic.
- The generated JSON is deterministic (sorted keys, stable formatting) so reruns produce small diffs.
- No second source of truth for locale codes (imports `SUPPORTED_LOCALES`).

## Verification

```bash
cd apps/discovery-ingest && uv run pytest tests/test_i18n_validate.py tests/test_i18n_translate.py
cd ../api && uv run pytest tests/test_enable_locale.py tests/test_seed_taxonomy.py tests/test_seed_i18n.py
cd ../web && npm test -- src/i18n
cd ../.. && ./ci.sh
```

Record strings translated per locale, validator rejections and repairs, neurons spent, and the review manifest status (all `machine` until reviewers sign) in [../run-ledger.md](../run-ledger.md). Operator: send each locale to a native-speaker reviewer, record the result in `review.json`, then run `enable_locale.py` per locale.

## Out of scope

Translating candidates, excerpts or any document text; machine-translation provenance; Arabic and right-to-left; a review UI; changing English or German copy.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/ui-translations
```

```text
test(ingest): describe UI translation validators and resume
feat(ingest): add translate-ui with glossary and validators
feat(i18n): add tr, ru, uk, pl and ro UI strings and taxonomy labels (machine, unreviewed)
feat(api): add guarded locale enablement
```
