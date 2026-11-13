# Interface locales: translate, review, enable

The interface speaks seven languages: `de` (source), `en`, `tr`, `ru`, `uk`, `pl` and `ro`. `de` and `en` are
written by hand. The other five are machine-translated by the engine that `TRANSLATION_ENGINE` selects (Azure AI Translator
by default; see [translation-engines.md](translation-engines.md)), then either reviewed by a native speaker or accepted by an
operator, and only then enabled. A locale that is not enabled is never served, even when its strings are in the
database.

The one list of locales is `SUPPORTED_LOCALES` in `apps/api/app/shared/locale.py`. Seeds never change
`supported_locale.enabled`; `enable_locale.py` is the only way to turn a locale on.

## Files

| File | What it holds |
| --- | --- |
| `apps/api/scripts/seed_data/translations/{de,en}.json` | The hand-written source strings. |
| `apps/api/scripts/seed_data/translations/{tr,ru,uk,pl,ro}.json` | Generated strings, same nested shape, sorted keys. |
| `apps/web/src/i18n/fallback/*.json` | Byte-identical copies of the files above, loaded lazily by the web app. |
| `apps/api/scripts/seed_data/taxonomy_translations.py` | Generated category names and descriptions, merged by `seed_taxonomy`. |
| `apps/api/scripts/seed_data/translations/review.json` | Per locale: `status` (`machine`, `reviewed` or `machine_accepted`), `reviewed_by`, `reviewed_on`, `accepted_by`, `accepted_on`, `model`, `command_version`. |

The frozen category contract (`category_contract_v1.json`) is never edited: it keeps `de` and `en` only.

## Translate a locale

Run from `apps/discovery-ingest` with the machine API key, the credentials of the engine that `TRANSLATION_ENGINE` selects (the
Azure key and region by default, or the Workers AI token for `llm`) and the proxy settings of your environment (see
[local-development.md](local-development.md)):

```bash
python -m discovery_ingest i18n translate-ui --locale tr
```

The command:

1. reads `en.json`, `de.json` and the active categories from the machine API;
2. expands plural families into the forms the locale needs (Russian `one/few/many/other`, Romanian
   `one/few/other`, Turkish `one/other`);
3. sends the German text to the translation engine (`TRANSLATION_ENGINE`) in batches of 40, with the English text
   and the key path as context and the per-locale glossary;
4. checks every result (placeholders, numbers, markup, glossary, layout length, untranslated English copies),
   asks once more for the strings that failed, and leaves the ones that still fail out of the files;
5. writes each finished batch whole, then `review.json` with `status: machine`.

The spend goes through the ledger of the engine. On `azure-translator` (the default) it is characters on the monthly
Azure ledger, and the run's report shows `characters_used`. On `llm` it is neurons on the shared ledger, which never goes
below `QUERY_EMBED_RESERVE` (request-time query embedding lives on it), and `--neuron-budget` bounds one `llm` run.

Exit codes: `0` done, `1` some strings were rejected (the JSON report lists each key with its problems), `2`
usage or setup error, `3` stopped early (quota or budget). Run the command again to continue: strings already in
the files are skipped, so a rerun, or a later copy change, translates only what is missing.

To translate a string again (for example after a glossary change), delete its key from the locale file and
rerun: the glossary version is not stored with a string, so an edit never invalidates existing text by itself.
Do not run two `translate-ui` commands for one locale at the same time: each rewrites the whole file.

Fix a rejected string by adjusting the glossary (`translation/glossary_data/<locale>.json`) or the allow list of
texts that may stay English (`i18n/data/unchanged.json`), then rerun. Never edit a generated file by hand without
recording the review.

## How the first five locales were made

`ru` was generated with `translate-ui` on Workers AI (`@cf/qwen/qwen3-30b-a3b-fp8`, `command_version` `1`). Its
Slavic plural forms were wrong, and the corrected forms are now in the files. `tr`, `uk`, `pl` and `ro` were not
produced by the pipeline: the daily Workers AI allowance ran out, so Claude Code (model `claude-sonnet-5-5`)
wrote them by hand from `en.json`, `de.json` and the category source, with the same glossary and the same
validators. Their `review.json` entries say `model: claude-sonnet-5-5` and `command_version: claude-code-manual-1`.
All five locales are `machine`, unreviewed and disabled. Review them like any other generated text (next section).
A later `translate-ui` run records its own model and command version for the strings it adds.

The hand-written glossary and allow-list entries need the same review. One entry was added with these locales:
`Extractor` in the Romanian allow list (the Romanian word equals the English one).

## Acceptance: two paths

A locale is enabled on one of two statuses in `review.json`. A person records each one. No tool is ever recorded
as the reviewer, and the model's output is never recorded as reviewed by the model.

| Status | Who records it | Fields | `machine_translated` once enabled |
| --- | --- | --- | --- |
| `reviewed` | The native speaker who reviewed the strings | `reviewed_by` (their name), `reviewed_on` (the date) | `machine_translated` false |
| `machine_accepted` | The operator who read enough of the strings to accept them | `accepted_by` (the operator's name), `accepted_on` (the date) | `machine_translated` true |

`model` and `command_version` stay as the generation run wrote them on both paths. `reviewed_by` and `accepted_by`
must name a person. The honesty test in `apps/discovery-ingest` refuses a translation engine or model name there
(`azure-translator`, `llm`, `claude…`, `qwen…`), so CI fails on such a manifest.

### Native review (`reviewed`)

1. Send the generated file and the category labels to a native speaker. Check the glossary terms
   first: they set the vocabulary of document translations as well.
2. Apply the reviewer's corrections to the locale file and `taxonomy_translations.py`. Keep the web copy
   identical (`cp` the seed file, or rerun the parity test).
3. Record the review in `review.json`: set `status` to `reviewed` and fill `reviewed_by` and `reviewed_on`.
   A `reviewed` entry without both does not load.

### Operator acceptance (`machine_accepted`)

Use this path when the machine strings are accepted without a native review. The operator, not a command, decides:

1. Reads enough of the locale file and the category labels to judge the strings, and checks the glossary terms.
2. Sets `status` to `machine_accepted` and fills `accepted_by` with the operator's own name and `accepted_on` with
   the date of the decision. A `machine_accepted` entry without both does not load.
3. Runs `enable_locale.py` for the locale (see Enable below).

Generating new strings for a reviewed or machine-accepted locale sets it back to `machine`, and the reviewer and
acceptance fields go with it: the new text needs its own review or acceptance.

## Enable

After the change is deployed and `python -m scripts.seed_i18n` and `python -m scripts.seed_taxonomy` have run:

```bash
cd apps/api
python -m scripts.enable_locale tr
```

The target database needs migration `20261112_locale_machine_flag` first: it adds `supported_locale.machine_translated`,
which the script writes. The production order is in [translation-engines.md](translation-engines.md#first-production-steps-operator).

The script enables the locale only when `review.json` says `reviewed` or `machine_accepted` and `ui_translation`
covers every German key (completeness 100). A `machine` status is refused, and the reason names all three statuses.
The same update sets `supported_locale.machine_translated`: true for `machine_accepted`, false for `reviewed`.
Otherwise the script exits 1 and says why. To switch a locale off again, set `supported_locale.enabled = false` in
the database.

## Checks

- `apps/web`: `npm test -- src/i18n` compares key sets, placeholders and plural forms (from `Intl.PluralRules`)
  of every locale file, and the web copies against the API seed files.
- `apps/api`: `pytest tests/test_enable_locale.py tests/test_locales_api.py tests/test_locale_migration.py
  tests/test_seed_taxonomy.py tests/test_seed_i18n.py`.
- `apps/discovery-ingest`: `pytest tests/test_i18n_validate.py tests/test_i18n_translate.py
  tests/test_i18n_manifest.py tests/test_i18n_committed_locales.py` (the last one runs the validators over the
  committed files, pins the Slavic plural forms and holds the honesty rule for `accepted_by`).
