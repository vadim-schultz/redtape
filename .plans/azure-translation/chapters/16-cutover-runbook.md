---
name: "Chapter 16 — Cutover and runbook"
overview: "Make Azure the default translation engine, keep llm selectable for rollback, pin the target-locale defaults to the embedding set with a parity test, and write the operator runbook for engines, the character ledger, the document share, the probe, backfills and rollback."
id: AZ16
depends_on:
  - AZ01
  - AZ02
  - AZ03
  - AZ04
  - AZ05
  - AZ06
  - AZ07
  - AZ08
  - AZ09
  - AZ10
  - AZ11
  - AZ12
  - AZ13
  - AZ14
  - AZ15
touches:
  - apps/discovery-ingest/discovery_ingest/translation/settings.py
  - apps/discovery-ingest/discovery_ingest/translation/locale_codes.py
  - apps/api/app/config.py
  - .github/workflows/discovery-translate.yml
  - docs/operations/translation-engines.md
  - docs/operations/scheduled-jobs.md
  - docs/operations/gha-budget.md
  - docs/operations/deployment-checklist.md
  - docs/operations/locales.md
  - render.yaml
  - apps/api/.env.example
  - apps/discovery-ingest/.env.example
  - apps/api/tests/test_discovery_operations_runbook.py
  - apps/discovery-ingest/tests/test_translate_workflow.py
execution: chapter-implementer
---

# Chapter 16 — Cutover and runbook

**Repo:** `redtape` (`apps/discovery-ingest`, `apps/api`, `.github/workflows`, `docs/operations`) · **Depends on:** chapters [01](01-ledger-resource.md)–[15](15-language-menu-flags.md) · **Decisions:** [D2](../gaps-and-decisions.md#d2--azure-ai-translator-f0-first-a-19-million-character-monthly-cap), [D3](../gaps-and-decisions.md#d3--languages-are-the-embedding-set), [D9](../gaps-and-decisions.md#d9--independent-of-the-claude-engine-the-cloudflare-translation-role-is-retired-later) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Azure becomes the default engine, with `llm` still one setting away. The target locales are pinned to the embedding set by a test. The operator runbook exists and the docs that list the ledger, caps and secrets agree with the code.

## Scope

- In: defaults, the workflow fallback, the parity test, the runbook, updates to the operations docs and their tests.
- Out: retiring the Cloudflare adapter (17), the operator's Render and GitHub settings (performed by the operator), the live drains.

## Design

1. **Default engine.** `translation/settings.py` `DEFAULT_ENGINE` becomes `"azure-translator"`. The workflow fallback `vars.TRANSLATION_ENGINE || 'llm'` becomes `|| 'azure-translator'`. Setting `TRANSLATION_ENGINE=llm` still selects the Cloudflare adapter, so rollback is one variable.
2. **Targets.** `TRANSLATION_TARGET_LOCALES` keeps its API default `en tr ru uk pl ro`. The ingest `DEFAULT_TARGET_LOCALES` (`translation/locale_codes.py`) must equal it, and both must equal `embedding_locales` minus `de`. A parity test enforces this.
3. **Runbook** `docs/operations/translation-engines.md`:
   - The engines and how `TRANSLATION_ENGINE` selects one.
   - Secrets and variables, with where each is set.
   - The character ledger, the monthly cap and the document share, with the cost table from the architecture.
   - The probe procedure and the glossary mode.
   - Backfill order: cards, then snapshots.
   - Rollback: set `TRANSLATION_ENGINE=llm`, and stop once the Azure monthly cap is reached.
   - The snapshot schedule variable.
   - The data-processing and region decision (O5).
4. **Operations docs** updated to match: `scheduled-jobs.md` (secrets, variables, the new precheck), `gha-budget.md` (note that translation uses characters), `deployment-checklist.md` (six budget resources and the cap table), `locales.md` (acceptance paths), `render.yaml` (comment listing the caps), both `.env.example` files.
5. **Doc tests.** `test_discovery_operations_runbook.py` `_CAP_DEFAULTS` and the "returns six resources" sentence are checked against the config.

## Files

| Path | Change |
| --- | --- |
| `translation/settings.py` | default engine |
| `translation/locale_codes.py` | parity with the API defaults |
| `.github/workflows/discovery-translate.yml` | fallback engine |
| `docs/operations/translation-engines.md` (new) | runbook |
| `docs/operations/scheduled-jobs.md`, `gha-budget.md`, `deployment-checklist.md`, `locales.md` | updated |
| `render.yaml`, `apps/api/.env.example`, `apps/discovery-ingest/.env.example` | comments and variables |
| `apps/discovery-ingest/tests/test_translate_workflow.py` | default engine and secret passing |
| `apps/api/tests/test_discovery_operations_runbook.py` | caps and resource count |
| `apps/discovery-ingest/tests/test_translation_locales_parity.py` (new) | target parity |

## Red tests

**Happy path**
- `Settings · with no TRANSLATION_ENGINE set, the engine is azure-translator`
- `Settings · TRANSLATION_ENGINE=llm still selects the Cloudflare adapter`
- `Workflow · the default engine expression is azure-translator`
- `Parity · ingest DEFAULT_TARGET_LOCALES equals the API default targets and embedding_locales minus de`
- `Docs · the runbook names every translation environment variable that settings read`
- `Docs · the deployment checklist lists six budget resources and the caps match the config`

**Negative path**
- `Settings · a misspelt engine name fails at load`
- `Workflow · Cloudflare translation secrets are passed only for the llm engine`
- `Docs · a new Azure environment variable without documentation fails the docs test`
- `Parity · drift between the ingest and API target lists fails the parity test`

## Green

Change the defaults first, then write the parity test, then the runbook and the docs until the doc tests pass.

## Refactor gate

- The engine default is defined in one place. The workflow reads the same name, and a test checks the two agree.
- The runbook is documentation; no code is duplicated into it. Cost figures are copied from the architecture once.
- House rules: no boolean flags, at most 3 parameters, about 100 lines per file.

## Verification

```bash
cd apps/discovery-ingest
.venv/bin/python -m pytest -q tests/test_translate_workflow.py tests/test_translation_locales_parity.py tests/test_settings_layering.py tests/test_azure_*.py
cd ../api && REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_discovery_operations_runbook.py tests/test_config_translation.py
cd ../.. && ./ci.sh
```

## Out of scope

Retiring the Cloudflare translation adapter (17), setting Render or GitHub values, running any drain or backfill.

## Operator steps after merge

1. Confirm O4 (quota reset) and O5 (data processing) are recorded.
2. On Render, set `TRANSLATION_TARGET_LOCALES` to `en tr ru uk pl ro` if it differs, and `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY` only if a non-default cap is wanted.
3. Confirm the GitHub secrets and the `TRANSLATION_ENGINE` variable from chapter 05 are present.
4. For each of `tr ru uk pl ro`, accept the strings by name and date in the manifest and run `enable_locale.py` (chapter 14).
5. Run `backfill_translations.py` for cards, then `backfill_snapshot_translations.py`, both as dry runs first.
6. Set `SNAPSHOT_TRANSLATE_SCHEDULE=enabled` after one inspected manual snapshot drain (chapter 11).
7. Record two runs on the coverage page and the monthly meter in the run ledger.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-16-cutover
# test(ingest)/test(api): ... (red), feat(ingest): default engine, feat(ops): workflow fallback, docs(ops): runbook
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
