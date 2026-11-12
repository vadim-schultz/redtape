---
name: "Chapter 05 — Probe, workflow and glossary gate"
overview: "Extend the translation probe to measure the Azure engine on real German units (glossary, placeholders, markup billing, throttling, billed versus estimated characters), set the glossary mode from the result, and wire the discovery-translate workflow to the Azure secrets and a character precheck. A live probe by the operator closes the chapter."
id: AZ05
depends_on:
  - AZ03
touches:
  - apps/discovery-ingest/discovery_ingest/translation/probe.py
  - apps/discovery-ingest/discovery_ingest/translation/probe_azure_report.py
  - apps/discovery-ingest/discovery_ingest/operations/translate_probe.py
  - apps/discovery-ingest/discovery_ingest/cli/translate/commands.py
  - apps/discovery-ingest/discovery_ingest/translation/settings.py
  - apps/discovery-ingest/discovery_ingest/translation/validate_glossary.py
  - apps/discovery-ingest/tests/fixtures/azure_probe_units.json
  - .github/workflows/discovery-translate.yml
  - apps/discovery-ingest/tests/test_translate_workflow.py
  - apps/discovery-ingest/tests/test_translate_cli.py
  - docs/operations/scheduled-jobs.md
execution: chapter-implementer
---

# Chapter 05 — Probe, workflow and glossary gate

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`, docs) · **Depends on:** [Chapter 03](03-character-meter-and-floor.md) · **Decisions:** [D2](../gaps-and-decisions.md#d2--azure-ai-translator-f0-first-a-19-million-character-monthly-cap), [D8](../gaps-and-decisions.md#d8--the-glossary-gate-is-set-by-a-live-probe) · **Open seams:** [O1](../gaps-and-decisions.md), [O2](../gaps-and-decisions.md), [O3](../gaps-and-decisions.md), [O4](../gaps-and-decisions.md), [O5](../gaps-and-decisions.md) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Measure the Azure engine on real units before it is trusted, and turn the result into a glossary mode and a recorded decision. Wire the workflow to the Azure secrets and a character precheck. Nothing in CI calls Azure; the live probe is an operator step.

## Scope

- In: probe cases and report, the glossary mode setting, validator behaviour for each mode, workflow secrets and precheck, workflow tests, scheduled-jobs docs.
- Out: the default engine and the target locales (chapter 16); snapshot probes (chapter 11 covers its own validation).

## Design

1. **Probe fixture.** `tests/fixtures/azure_probe_units.json` holds a fixed sample of about 20 German card units per locale. It is exported by the operator from production, contains only public procedure titles and descriptions, and is committed after review. It is not regenerated on each run.
2. **Probe cases** (`probe.py`, reports in `probe_azure_report.py`):
   - Adherence: the glossary check on every unit, counted per locale.
   - Placeholders and URLs: each token survives the round trip.
   - Markup billing: a small set of HTML-tagged inputs, to see whether tags are billed (O2).
   - Throttling: one call is repeated at the configured minimum interval, to see whether the service answers 429 and what it returns.
   - Billed versus estimated: the sum of `X-metered-usage` against the estimate, per call.
3. **Report** (JSON): per locale, the share of valid units; glossary findings; placeholder failures; billed and estimated characters; whether markup is billed; the recommended glossary mode.
4. **Glossary mode.** `TRANSLATION_GLOSSARY_MODE` (`strict` or `advisory`, default `strict`). In `strict`, a glossary-adherence finding fails the unit. In `advisory`, the finding is logged and counted but the unit passes. The probe recommends `strict` only when every target locale reaches at least 90% valid units, and otherwise `advisory`. The chosen mode is recorded by the operator in the run ledger.
5. **Workflow** (`discovery-translate.yml`):
   - Pass `AZURE_TRANSLATOR_KEY`, `AZURE_TRANSLATOR_REGION` and `AZURE_TRANSLATOR_ENDPOINT` from secrets, only when `TRANSLATION_ENGINE` is `azure-translator`.
   - The neuron precheck runs only for the neuron engine.
   - For Azure, a `budget show --require-remaining azure_translator_chars=<AZURE_TRANSLATOR_MIN_REMAINING_CHARS>` precheck exits 3 when too little remains, and the job skips without failing. The minimum defaults to 20,000 characters.
   - The default engine remains `llm` here (chapter 16 changes it).
6. **Docs.** `scheduled-jobs.md` gets the new secrets, variables and the precheck.

## Files

| Path | Change |
| --- | --- |
| `translation/probe.py`, `translation/probe_azure_report.py` (new) | cases and report |
| `operations/translate_probe.py`, `cli/translate/commands.py` | `--engine azure-translator`; a report option |
| `translation/settings.py` | `TRANSLATION_GLOSSARY_MODE` |
| `translation/validate_glossary.py` | advisory versus strict |
| `tests/fixtures/azure_probe_units.json` (new) | reviewed sample |
| `.github/workflows/discovery-translate.yml` | Azure secrets; conditional precheck |
| `tests/test_translate_workflow.py` | `SECRETS` set and conditional steps |
| `tests/test_translate_cli.py`, `tests/golden/help/translate*.txt` | probe options |
| `docs/operations/scheduled-jobs.md` | secrets, variables, precheck |

## Red tests

**Happy path**
- `Probe · the report gives per-locale valid share, glossary findings, placeholder survival and billed and estimated characters`
- `Probe · the recommended mode is strict only when every locale reaches 90% valid units`
- `Settings · TRANSLATION_GLOSSARY_MODE accepts strict and advisory and defaults to strict`
- `Validator · advisory mode records a glossary finding without failing the unit; strict fails it`
- `Workflow · Azure secrets are passed only when the engine is azure-translator`
- `Workflow · the character precheck exits 3 when remaining is below the minimum`

**Negative path**
- `Probe · no key stops before any HTTP call, with a message naming the variable`
- `Probe · a test run makes no network call (fake transport only)`
- `Workflow · engine azure-translator with no secret fails at the precheck with a message, not a silent skip`
- `Settings · an unknown glossary mode fails at load`

## Green

The smallest change for each red test. The probe reuses the existing drain and validators, so it measures what production will do.

## Refactor gate

- The report builder is a separate module. Each probe case is a function of about 5 lines, and the cases are listed in one table.
- The workflow change is a conditional by engine, expressed once, not repeated per step.
- Rule of three applies to the secret-passing expressions. Keep one named set.
- House rules: about 100 lines per file, no boolean flags, at most 3 parameters.

## Verification

```bash
cd apps/discovery-ingest
.venv/bin/python -m pytest -q tests/test_translate_workflow.py tests/test_translate_cli.py tests/test_translate_probe*.py tests/test_azure_*.py tests/test_settings_layering.py
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy discovery_ingest
cd ../.. && ./ci.sh
```

**Live probe (operator, once, recorded):** with the key in the shell and never committed, run `translate probe --engine azure-translator` on the fixture. Spend no more than 10,000 characters. Record the JSON report, the glossary mode and the markup-billing answer in the chief's run ledger, and resolve O1 to O4 there.

## Out of scope

Engine default and target locales (16), snapshot validation rules (11), HTML-mode glossary (only if the probe shows it works under the current API, as a later chapter), the document share.

## Operator steps after merge

1. Create the Azure Translator resource (F0, EU region) after O5 is recorded.
2. Put `AZURE_TRANSLATOR_KEY`, `AZURE_TRANSLATOR_REGION` and, if custom, `AZURE_TRANSLATOR_ENDPOINT` in the `discovery-translate` GitHub environment.
3. Run the live probe as above and record the glossary mode.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-05-probe-and-workflow
# test(ingest): ... (red), feat(ingest): ... (green), feat(ops): ... (workflow), docs(ops): ...
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
