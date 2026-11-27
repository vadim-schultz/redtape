# C3 — Local translation

**Depends on:** C0 · **Batch:** 2 · **Branch:** `feat/local-queue-drain-translation`

## Goal

Add a local translation engine, with its own lane in the API, that takes first translations of the target locales before Azure does. Azure then has its monthly characters for upgrades (`UPGRADE_BASE`), and first passes no longer wait for Azure's quota.

## Measurement gate first (no code)

The architecture records no authoritative German benchmark. C3 makes one.

1. Build a German sample of 200 units from stored candidate titles and descriptions, the shape `translation/units.py` expects. Include glossary terms and at least 20 units with placeholders or markup, so the validator is exercised.
2. For each candidate engine, translate the sample into en, tr, ru, uk, pl and ro in the scratchpad, using CTranslate2 int8 if it installs. Record speed (units per second on 28 threads) and the validation pass rate from `translation/validate.py`. The Apache-2.0 candidates are MADLAD-400-3B-MT (all six locales) and Opus-MT for de-en, de-pl and de-uk. The Hub returned no de-tr, de-ru or de-ro Opus-MT repository, so those three locales go to MADLAD-400 only. NLLB-200 distilled 600M (CC-BY-NC-4.0) and Tower-Plus-9B (CC-BY-NC-SA-4.0) join the benchmark too: the project is non-commercial (D16).
3. Score quality on a fixed 50-unit subset with a reference: the Azure output for the same units, already stored in the database. Use chrF, and report it per locale. Note that Azure is the reference, not the truth; the gate measures agreement with the current production output.
4. Gate: validation pass rate ≥ 95% per locale and chrF ≥ the value agreed with the operator (default: within 5 points of the best engine for that locale). A locale that fails the gate is not served locally; it stays on Azure. The decision goes to O2.

## Slices (red → green → refactor each)

### Slice 3a — engine registration

- **Happy:** `build_engine("local-madlad", EngineConfig(target_locales=("en","tr","ru","uk","pl","ro")))` returns an engine whose `name` is `local-madlad`, `usage_unit` is `"local"`, and `limits` is a `CallLimits`.
- **Negative:** building the same engine with a locale it does not map (`"fr"`) raises `UnmappedLocaleError` naming `fr`. The registry stays unchanged.

### Slice 3b — translate

- **Happy:** `translate(batch)` with two German units returns two `TranslationOutcome` results, in order, both passing `validate`. `usage` is a `Usage` with unit `local`.
- **Negative:** an engine output that drops a placeholder (`{name}` in the source, absent in the output) fails validation. Because `repairs` is `False` for this engine, the unit is failed with `UnusableOutputError`, not repaired.

### Slice 3c — lane (API)

- **Happy:** a claim with `engine="local-madlad"` returns only target-locale first translations inside the local lane's band.
- **Negative:** the same claim does not return a task whose locale is outside the lane, nor an upgrade row (`UPGRADE_BASE`). The test asserts both are absent from the response.

### Slice 3d — meter

- **Happy:** `open_run_meter("local", plan)` returns a meter that bounds the drain by the run budget, reserves nothing from the ledger, and reports `used` in the drain tally.
- **Negative:** `open_run_meter` with a unit that has no meter (an unknown string) raises `NoMeterForUnitError`, as today.

## Green

- Add `"local"` to `UsageUnit` in `translation/units.py`, and a `LocalMeter` in `translation/` that counts units, not characters or neurons.
- Implement one `TranslationEngine` for each engine that wins the benchmark for some locale (O2), for example `local-madlad`, `local-nllb` or `local-tower`. Register each locale map through `register_locale_map`.
- Add the lane to `features/translation/lanes.py`. Set the local lane's locales through configuration, default `en tr ru uk pl ro` minus any locale that failed the gate.
- Keep Azure's lane as it is.

## Refactor

- `translate_meter._OWN_METERS` maps a unit to a meter factory. With `characters`, `subscription` and `local` it has three entries, so keep it as a table and do not add branches.
- `lanes.py` now has three engines (Azure, `llm`, local). Check the total: the table form is already the rule-of-three answer. Confirm no branch chain was added.
- The local engine and the `llm` engine both build a `TranslationBatch` prompt. Extract any duplicated prompt helper into `translation/` and parameterise it by the language table.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "translation and local" -q
cd apps/api && .venv/bin/python -m pytest tests -k "translation and lane" -q
cd apps/api && ./ci.sh
```

The lane change touches the API, so the API `./ci.sh` runs on the chapter branch as well as the discovery package.

## Exit

- The German benchmark and the per-locale gate decision are recorded in the ledger (O2 closed).
- One bounded local translate drain completes against the live queue. Azure's characters for the same period do not grow for the first passes the local engine took.
- The local lane's translated count is visible in the translation summary that the monitor reads (C7).
