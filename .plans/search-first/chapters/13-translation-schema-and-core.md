---
name: "Chapter 13 — Translation schema and core"
overview: "Add the stored-translation and translation-task tables, a shared translation core (engine, glossary, validators), and a probe that chooses the translation engine and costs the whole corpus before any translation is queued."
id: C13
depends_on:
  - C3
touches:
  - apps/api/app/models/
  - apps/api/alembic/versions/
  - apps/api/app/config.py
  - apps/api/tests/
  - apps/discovery-ingest/discovery_ingest/translation/
  - apps/discovery-ingest/discovery_ingest/cli/translate/
  - apps/discovery-ingest/tests/
execution: chapter-implementer
todos:
  - id: models-migration
    content: "Add CandidateTranslation and TranslationTask models and one migration."
    status: pending
  - id: settings
    content: "Add validated translation target and engine settings."
    status: pending
  - id: core
    content: "Add the shared translation core: translator protocol, LLM implementation, glossary and base validators."
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

Lay the foundation for translating document text once and storing it: where translations live, what exactly is translated, and which engine does it at what cost. Nothing is queued or translated yet.

## Design decisions

- **What is translated (the translation unit).** The two fields a card shows: the candidate **title** (German, `title_i18n["de"]`) and the card **description** (the best mention's excerpt as served today by `features/candidates/repository/descriptions.py`, capped at `DESCRIPTION_MAX_LENGTH`). Not every mention excerpt: that would multiply cost, while title plus description is enough for short queries and for the pop-over (chapter 18 measures whether more is needed). Source language is `de`. `source_hash = sha256(UNIT_RECIPE_VERSION + title + description)`, so a change in the German source makes a stored translation *stale*.
- **Targets.** `TRANSLATION_TARGET_LOCALES` (default `en tr ru uk pl ro`), validated as a subset of `SUPPORTED_LOCALES` minus `de`. Translating a locale does not enable it for the interface (that stays gated by chapter 11).
- **Translated once.** A row is written once per `(candidate, locale)`. It is re-translated only when `source_hash` changes, at low priority, and never over a `human` row. The pop-over and search read stored rows only; there is no live translation anywhere.
- **Tables** (one migration `YYYYMMDD_translation_schema`, after chapter 3's):
  - `candidate_translation(candidate_id FK ON DELETE CASCADE, locale String(16), title Text, description Text null, source_hash String(64), source enum translation_source (mt|human) default mt, model String(100) null, created_at, updated_at)`, primary key `(candidate_id, locale)`;
  - `translation_task(id uuid PK, candidate_id FK ON DELETE CASCADE, locale, source_hash, status work_task_status, priority int default 100, attempt_count int default 0, not_before, claimed_at, claimed_by_api_key_id FK api_key ON DELETE SET NULL, lease_expires_at, last_error Text, created_at, updated_at)`; partial unique index on `(candidate_id, locale)` where status is `pending` or `claimed`; index `(status, priority, created_at)`. The status enum is chapter 3's `work_task_status`.
  - Models in `apps/api/app/models/translation.py`, exported from `app/models/__init__.py`.
- **Translation core** in `apps/discovery-ingest/discovery_ingest/translation/` (shared with chapter 11):
  - `units.py`: typed `TranslationUnit` and `TranslationResult` DTOs;
  - `engine.py`: a `Translator` protocol; `LlmTranslator` over the existing `LlmClient` (`extract/llm/`) with JSON-schema output, per-locale glossary injection and `NeuronMeter` reserve/settle/refund; an optional `MtTranslator` for a dedicated translation model if the probe favours it;
  - `glossary.py` with a per-locale data file: fixed renderings for domain terms (*Antrag*, *Bürgeramt*, *Nachweis*, …) and a do-not-translate list (proper nouns, agency names, law abbreviations);
  - `validate.py`: base validators, each a small pure function — non-empty, length ratio within bounds, numbers, dates, URLs and legal citations (for example "§ 35") preserved exactly, no added markup, glossary adherence, not an unchanged copy of the source unless it is a proper noun or very short.
- **Probe.** `python -m discovery_ingest translate probe --locale <code> --sample 50 --engine llm|mt` translates a fixed, reproducible sample of real candidates, reports the validator pass rate, neurons per unit, latency and the projected neurons for the whole corpus per locale and in total (and the days that takes at the daily budget share), and writes a side-by-side sheet (German, translation) for native-speaker spot checks. It writes nothing to the database.
- **Decision gate (D13).** The probe output is recorded in the run ledger and the engine, model and rollout pace are settled in [../gaps-and-decisions.md](../gaps-and-decisions.md). If the full-corpus cost does not fit the neuron budget share, the options are a cheaper engine, fewer locales, or priority-limited coverage (highest-confidence candidates first); the plan does not assume the LLM fits.
- Reuse: no new HTTP client, throttle or error taxonomy; the core imports `extract/llm` pieces.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/translation.py`, `app/models/__init__.py` | Models. |
| `apps/api/alembic/versions/YYYYMMDD_translation_schema.py` | Migration. |
| `apps/api/app/config.py` | `TRANSLATION_TARGET_LOCALES`, `TRANSLATION_UNIT_RECIPE_VERSION`. |
| `apps/discovery-ingest/discovery_ingest/translation/units.py`, `engine.py`, `glossary.py`, `validate.py`, `glossary_data/` | Core. |
| `apps/discovery-ingest/discovery_ingest/cli/translate/` | `translate probe`, registered in `cli/main.py`. |
| `apps/api/tests/test_translation_models.py` | Round trips and constraints. |
| `apps/discovery-ingest/tests/test_translation_validate.py`, `test_translation_engine.py`, `test_translate_probe.py` | Core and probe tests with a fake LLM. |

## Red tests

### Happy path

- `translation · stores a title and description per candidate and locale and finds them by key`.
- `translation task · one open task per candidate and locale; a completed one does not block a new one`.
- `migration · upgrade, downgrade, upgrade round trip` and `alembic check` pass.
- `validate · accepts a faithful translation` with numbers, a "§" citation, a URL and a glossary term preserved.
- `engine · LlmTranslator returns one result per unit in order and charges the meter`.
- `probe · reports pass rate, neurons per unit and projected corpus cost` from canned responses.

### Negative path

- `validate · rejects changed numbers, dropped citations, added markup, a glossary violation, an extreme length ratio or an unchanged copy`.
- `engine · a quota error releases the meter reservation and raises the stop reason`.
- `settings · a target locale that is de or unsupported fails at load`.
- `translation · a duplicate (candidate, locale) row is refused; deleting a candidate cascades`.
- `probe · a sample that fails validation is reported, not silently dropped`.

## Green

1. Models and migration; `check_migrations.sh`.
2. Validators, glossary and the LLM translator against fake clients.
3. The probe; run it once per target locale on the operator machine and record the output.

## Refactor gate

- Validators are separate pure functions, one concern each; the engine orchestrates them.
- Glossary and do-not-translate lists are data files, not code.
- No `Any`, no boolean flags, at most 3 parameters (use DTOs); docstrings present.
- The core has no knowledge of candidates or the API; it translates units.

## Verification

```bash
cd apps/api
uv run pytest tests/test_translation_models.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
bash scripts/check_migrations.sh
cd ../discovery-ingest
uv run pytest tests/test_translation_validate.py tests/test_translation_engine.py tests/test_translate_probe.py
cd ../.. && ./ci.sh
```

Record the migration id, the probe reports (pass rate, neurons per unit, projected totals), the spot-check sheets' reviewer notes, and the engine decision in [../run-ledger.md](../run-ledger.md).

## Out of scope

Enqueueing or translating candidates (chapters 14 and 15), serving translations (chapter 17), search text and embeddings for translated locales (chapter 16), UI strings (chapter 11), a human-review tool.

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
