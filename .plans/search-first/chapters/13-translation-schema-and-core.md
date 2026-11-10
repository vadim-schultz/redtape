---
name: "Chapter 13 — Translation schema and core"
overview: "Add the translation index and task tables, an R2-backed translation store, a shared translation core with a pluggable engine port, a registry and a conformance suite (Cloudflare first, Azure Translator possible later), and a probe that chooses the engine and costs the whole corpus before any translation is queued."
id: C13
depends_on:
  - C3
touches:
  - apps/api/app/models/
  - apps/api/alembic/versions/
  - apps/api/app/config.py
  - apps/api/app/features/translation/store.py
  - apps/api/tests/
  - apps/discovery-ingest/discovery_ingest/translation/
  - apps/discovery-ingest/discovery_ingest/cli/translate/
  - apps/discovery-ingest/tests/
execution: chapter-implementer
todos:
  - id: models-migration
    content: "Add the CandidateTranslation index and TranslationTask models and one migration."
    status: pending
  - id: translation-store
    content: "Add TranslationStore over the existing ObjectStore port: key layout, payload DTO, write, read, delete."
    status: pending
  - id: settings
    content: "Add validated translation target and engine settings."
    status: pending
  - id: core
    content: "Add the shared translation core: TranslationEngine port, registry, usage meters, locale-code maps, the Cloudflare LLM adapter, glossary and base validators."
    status: pending
  - id: conformance
    content: "Add the adapter conformance suite that every registered engine must pass, and the how-to-add-an-adapter checklist."
    status: pending
  - id: probe
    content: "Add a probe that compares engines on a fixed sample, reports cost and validator pass rate, and writes a spot-check sheet."
    status: pending
  - id: tests
    content: "Add model, constraint, validator, translator and probe tests."
    status: pending
---

# Chapter 13 — Translation schema and core

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`)
**Depends on:** [Chapter 3](03-search-schema.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Lay the foundation for translating document text once and storing it: where translations live (R2, with an index in Postgres), what exactly is translated, and which engine does it at what cost, behind an adapter port so a second provider can be plugged in later. Nothing is queued or translated yet.

## Design decisions

- **What is translated (the translation unit).** The two fields a card shows: the candidate **title** (German, `title_i18n["de"]`) and the card **description** (the best mention's excerpt as served today by `features/candidates/repository/descriptions.py`, capped at `DESCRIPTION_MAX_LENGTH`). Not every mention excerpt: that would multiply cost, while title plus description is enough for short queries and for the pop-over (chapter 18 measures whether more is needed). Source language is `de`. `source_hash = sha256(UNIT_RECIPE_VERSION + title + description)`, so a change in the German source makes a stored translation *stale*.
- **Targets.** `TRANSLATION_TARGET_LOCALES` (default `en tr ru uk pl ro`), validated as a subset of `SUPPORTED_LOCALES` minus `de`. Translating a locale does not enable it for the interface (that stays gated by chapter 11).
- **Translated once.** A row is written once per `(candidate, locale)`. It is re-translated only when `source_hash` changes, at low priority, and never over a `human` row. The pop-over and search read stored translations only; there is no live translation anywhere.
- **Tables** (one migration `YYYYMMDD_translation_schema`, after chapter 3's):
  - `candidate_translation(candidate_id FK ON DELETE CASCADE, locale String(16), source_hash String(64), source enum translation_source (mt|human) default mt, engine String(50), model String(100) null, storage_key String(255), content_sha256 String(64), size_bytes Integer, created_at, updated_at)`, primary key `(candidate_id, locale)`. No title or description columns: the text lives in R2 (decision D17) and this row is the index (existence, staleness, provenance, object key);
  - `translation_task(id uuid PK, candidate_id FK ON DELETE CASCADE, locale, source_hash, status work_task_status, priority int default 100, attempt_count int default 0, not_before, claimed_at, claimed_by_api_key_id FK api_key ON DELETE SET NULL, lease_expires_at, last_error Text, created_at, updated_at)`; partial unique index on `(candidate_id, locale)` where status is `pending` or `claimed`; index `(status, priority, created_at)`. The status enum is chapter 3's `work_task_status`.
  - Models in `apps/api/app/models/translation.py`, exported from `app/models/__init__.py`.
- **Translation store** (`apps/api/app/features/translation/store.py`). `TranslationStore` wraps the existing `ObjectStore` port (`app/shared/object_store/port.py`, metered by the same provider the artifact routes use). It builds the key `translations/v1/{candidate_id}/{locale}/{unit}/{content_sha256}.json` (`unit` is `card`; the segment is the seam for full-document translations, O16), encodes and decodes a `TranslationPayload` DTO (`schema`, `unit`, `locale`, `title`, `description`, `source_hash`, `source`, `engine`, `model`) as canonical UTF-8 JSON, and returns `StoredObject(key, content_sha256, size_bytes)` from `write(payload)`; `read(key)` returns the payload or raises a typed `TranslationObjectMissingError`; `delete(key)` is a no-op on a missing key. It uses `require_store`, so an unconfigured store is a typed `ObjectStoreUnavailableError`. Tested against the in-memory store (`shared/object_store/memory.py`).
- **Translation core** in `apps/discovery-ingest/discovery_ingest/translation/` (shared with chapter 11). Cloudflare Workers AI is the first provider because it is known to the team; the core is built so another provider is an adapter, not a rewrite (decision D16):
  - `units.py`: typed DTOs `TranslationUnit`, `TranslationBatch(source_locale, target_locale, units, glossary)`, `TranslationOutcome(results, usage, model)` and `Usage(unit: "neurons" | "characters", amount)`;
  - `engine.py`: the `TranslationEngine` Protocol (`name`, `usage_unit`, `translate(batch) -> TranslationOutcome`, `estimate(batch) -> Usage`). It knows nothing about candidates, queues, the API or any provider;
  - `registry.py`: `register_engine(name, factory)` and `build_engine(name, config)`. `TRANSLATION_ENGINE` (worker setting, default `llm`) is validated at load against the registered names; an unknown name fails with the list of registered ones. Chapters 11 and 15 and the probe get their engine only from here;
  - `meter.py`: a `UsageMeter` Protocol (`reserve`, `settle`, `refund`, `remaining`) and `NeuronUsageMeter` over the existing `NeuronMeter`/`BudgetService`. Drains choose the meter by the engine's `usage_unit`; there is no characters meter yet, and asking for one raises a clear "no meter for unit" error until the first character-billed adapter ships (O17);
  - `locale_codes.py`: per-engine map from our locale codes to the provider's, which must cover every target locale (identity for the Cloudflare adapters);
  - `adapters/cloudflare_llm.py`: `LlmTranslator` over the existing `LlmClient` (`extract/llm/`) with JSON-schema output, glossary injection into the prompt and neuron usage; `adapters/cloudflare_mt.py` only if the probe favours a dedicated Workers AI translation model. Each registers itself by name. Provider clients, endpoints and tokens are imported only inside an adapter;
  - `glossary.py` with a per-locale data file: fixed renderings for domain terms (*Antrag*, *Bürgeramt*, *Nachweis*, …) and a do-not-translate list (proper nouns, agency names, law abbreviations). An adapter applies it in the way its provider supports (prompt text for an LLM; a provider dictionary feature for a classic MT service, later); the validators check adherence regardless of how;
  - `validate.py`: base validators, each a small pure function — non-empty, length ratio within bounds, numbers, dates, URLs and legal citations (for example "§ 35") preserved exactly, no added markup, glossary adherence, not an unchanged copy of the source unless it is a proper noun or very short.
- **Adapter conformance suite.** `apps/discovery-ingest/tests/translation_engine_contract.py` is parametrised over the registry. Each adapter's own test module supplies a fake transport (no network in CI) and the suite asserts, for every registered engine: one result per unit in order; a short response is an error, not silently dropped units; placeholders, numbers, URLs and legal citations survive a faithful round trip; every target locale code maps; usage is reported in the engine's declared unit and settles on actuals; provider failures map onto the categories the drains already act on (quota, transient, unauthorised, permanent); the token never appears in errors or logs. A future adapter passes the same suite before it can be selected.
- **Adding an adapter later** is a checklist, written into the chapter's PR description and carried into `docs/operations/translation-engines.md` by chapter 18: implement the port, add its locale map, register it, add its credentials as a GitHub secret, supply a fake transport and pass the conformance suite, run the probe with `--engine <name>` and record the comparison under D13. Azure AI Translator is the planned case (O17); no Azure code, key or dependency is added now.
- **Probe.** `python -m discovery_ingest translate probe --locale <code> --sample 50 --engine <registered name>` translates a fixed, reproducible sample of real candidates, reports the validator pass rate, usage per unit in the engine's own unit (neurons or characters), latency and the projected usage for the whole corpus per locale and in total (and the days that takes at the daily budget share, for neuron-metered engines), and writes a side-by-side sheet (German, translation) for native-speaker spot checks. It writes nothing to the database.
- **Decision gate (D13).** The probe output is recorded in the run ledger and the engine, model and rollout pace are settled in [../gaps-and-decisions.md](../gaps-and-decisions.md). If the full-corpus cost does not fit the neuron budget share, the options are a cheaper engine, fewer locales, or priority-limited coverage (highest-confidence candidates first); the plan does not assume the LLM fits.
- Reuse: no new HTTP client, throttle or error taxonomy; the Cloudflare adapters import `extract/llm` pieces and a future adapter maps its provider's errors onto the same categories.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/translation.py`, `app/models/__init__.py` | Models (index row, task). |
| `apps/api/app/features/translation/store.py` | `TranslationStore`, `TranslationPayload`, `StoredObject`. |
| `apps/api/alembic/versions/YYYYMMDD_translation_schema.py` | Migration. |
| `apps/api/app/config.py` | `TRANSLATION_TARGET_LOCALES`, `TRANSLATION_UNIT_RECIPE_VERSION`. |
| `apps/discovery-ingest/discovery_ingest/translation/units.py`, `engine.py`, `registry.py`, `meter.py`, `locale_codes.py`, `glossary.py`, `validate.py`, `glossary_data/` | Core. |
| `apps/discovery-ingest/discovery_ingest/translation/adapters/cloudflare_llm.py` (and `cloudflare_mt.py` if chosen) | Cloudflare adapters. |
| `apps/discovery-ingest/discovery_ingest/cli/translate/` | `translate probe`, registered in `cli/main.py`. |
| `apps/api/tests/test_translation_models.py`, `test_translation_store.py` | Round trips, constraints, store layout and round trip. |
| `apps/discovery-ingest/tests/test_translation_validate.py`, `test_translation_engine.py`, `test_translation_registry.py`, `translation_engine_contract.py`, `test_translate_probe.py` | Core, registry, conformance suite and probe tests with fake transports. |

## Red tests

### Happy path

- `translation · an index row per candidate and locale is found by key and carries engine, model, hash and object key`.
- `store · writes a payload under the content-addressed key, reads it back identical, and the content hash and size match`.
- `registry · build_engine returns the registered adapter; the conformance suite passes for the Cloudflare adapter`.
- `translation task · one open task per candidate and locale; a completed one does not block a new one`.
- `migration · upgrade, downgrade, upgrade round trip` and `alembic check` pass.
- `validate · accepts a faithful translation` with numbers, a "§" citation, a URL and a glossary term preserved.
- `engine · LlmTranslator returns one result per unit in order and reports usage in neurons`.
- `registry · a fake second adapter (characters unit, its own locale map) can be registered and selected without changes elsewhere` (the proof of the seam).
- `probe · reports pass rate, neurons per unit and projected corpus cost` from canned responses.

### Negative path

- `validate · rejects changed numbers, dropped citations, added markup, a glossary violation, an extreme length ratio or an unchanged copy`.
- `engine · a quota error releases the meter reservation and raises the stop reason`.
- `registry · an unknown TRANSLATION_ENGINE fails at load and lists the registered names`.
- `conformance · an adapter that drops a unit, mangles a placeholder or leaks the token fails the suite` (checked with a deliberately broken fake).
- `store · a missing object raises TranslationObjectMissingError; an unconfigured store raises the typed unavailable error; deleting a missing key is a no-op`.
- `meter · asking for a characters meter raises a clear no-meter error`.
- `settings · a target locale that is de or unsupported fails at load`.
- `translation · a duplicate (candidate, locale) row is refused; deleting a candidate cascades`.
- `probe · a sample that fails validation is reported, not silently dropped`.

## Green

1. Models and migration; `check_migrations.sh`.
2. Validators, glossary and the LLM translator against fake clients.
3. The probe; run it once per target locale on the operator machine and record the output.

## Refactor gate

- Validators are separate pure functions, one concern each; the engine port stays free of orchestration, which lives in the drain and probe.
- Only adapter modules import a provider client; a grep for provider names outside `translation/adapters/` is empty.
- Glossary and do-not-translate lists are data files, not code.
- No `Any`, no boolean flags, at most 3 parameters (use DTOs); docstrings present.
- The core has no knowledge of candidates or the API; it translates units.

## Verification

```bash
cd apps/api
uv run pytest tests/test_translation_models.py tests/test_translation_store.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
bash scripts/check_migrations.sh
cd ../discovery-ingest
uv run pytest tests/test_translation_validate.py tests/test_translation_engine.py \
  tests/test_translation_registry.py tests/test_translate_probe.py
cd ../.. && ./ci.sh
```

Record the migration id, the adapters passing the conformance suite, the store round trip, the probe reports (pass rate, usage per unit, projected totals), the spot-check sheets' reviewer notes, and the engine decision in [../run-ledger.md](../run-ledger.md).

## Out of scope

Enqueueing or translating candidates (chapters 14 and 15), serving translations (chapter 17), search text and embeddings for translated locales (chapter 16), UI strings (chapter 11), a human-review tool, the Azure Translator adapter and its characters meter (O17), full-document translation units (O16).

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/translation-schema-and-core
```

```text
test(api): describe stored translations and translation tasks
feat(api): add translation schema
feat(ingest): add translation core and probe
```
