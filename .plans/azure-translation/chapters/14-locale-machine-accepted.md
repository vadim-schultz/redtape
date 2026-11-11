---
name: "Chapter 14 — Machine-accepted interface locales"
overview: "Let an operator enable an interface locale on machine-made strings with a recorded decision that names the operator and the date, instead of a native review. The API exposes machine_translated per locale. No tool is ever recorded as a reviewer."
id: AZ14
depends_on: []
touches:
  - apps/api/scripts/enable_locale.py
  - apps/api/scripts/seed_data/review_manifest.py
  - apps/api/app/models/
  - apps/api/app/schema/locale/read.py
  - apps/api/app/features/locales/
  - apps/api/alembic/versions/
  - apps/discovery-ingest/discovery_ingest/i18n/manifest.py
  - apps/discovery-ingest/tests/test_i18n_committed_locales.py
  - apps/discovery-ingest/tests/test_i18n_manifest.py
  - apps/api/tests/test_enable_locale.py
  - apps/api/tests/test_locales_api.py
  - openapi.schemas.json
  - apps/web/src/services/localesApi.ts
  - apps/web/src/contexts/LocaleContext.test.tsx
  - docs/operations/locales.md
execution: chapter-implementer
---

# Chapter 14 — Machine-accepted interface locales

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`, `apps/web`, `docs/operations`) · **Depends on:** none · **Decisions:** [D4](../gaps-and-decisions.md#d4--interface-locales-are-enabled-on-machine-output), [D5](../gaps-and-decisions.md#d5--machine-output-is-labelled-and-no-tool-is-ever-the-reviewer), [O6](../gaps-and-decisions.md) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

A locale can be enabled on machine-made strings once an operator has accepted them by name and date. The enabled locale is marked `machine_translated` in the API. The honesty test still forbids naming a tool as the reviewer.

## Scope

- In: manifest status, the enable gate, the migration, the locales read model, the honesty test, docs, web type and fixtures.
- Out: the switcher's flags and note (15), any change to the five manifests' statuses (done by the operator after merge).

## Design

1. **Statuses.** The manifest status literal becomes `machine | reviewed | machine_accepted`, in `scripts/seed_data/review_manifest.py` and in `discovery_ingest/i18n/manifest.py`. `machine_accepted` requires `accepted_by` (a non-empty person's name) and `accepted_on` (an ISO date). Both literals must agree.
2. **Gate.** `enable_locale.py` (`_review_problem`) accepts `reviewed` or `machine_accepted`. Its completeness rule is unchanged: 100% of German keys. A `machine` status is refused, and the message names the three statuses.
3. **Flag.** `enable_locale` sets `machine_translated = (status == "machine_accepted")` in the same UPDATE as `enabled`. The value is derived from the status, not passed as a boolean argument.
4. **Migration.** `supported_locale.machine_translated` is a boolean, not null, default false.
5. **Read.** `LocaleRead` gains `machine_translated: bool`. `GET /api/v1/locales` returns it. The OpenAPI snapshot and `openapi.schemas.json` are regenerated.
6. **Honesty test.** `test_the_committed_manifest_marks_every_locale_machine_and_unreviewed_with_honest_provenance` keeps its rule that committed `machine` entries are unreviewed. A new check asserts that `accepted_by` is never an engine name (`azure-translator`, `llm`, `claude…`, `qwen…`).
7. **Web.** `LocaleRow` gains `machine_translated`. Fixtures in `LocaleContext.test.tsx` and `AppMenu.test.tsx` are updated.
8. **Docs.** `docs/operations/locales.md` describes the two acceptance paths and says who records each.

## Files

| Path | Change |
| --- | --- |
| `apps/api/scripts/seed_data/review_manifest.py` | status literal; `accepted_by`, `accepted_on` |
| `apps/discovery-ingest/discovery_ingest/i18n/manifest.py` | the same literal |
| `apps/api/scripts/enable_locale.py` | gate and flag |
| `apps/api/alembic/versions/` | `supported_locale.machine_translated` |
| `apps/api/app/models/` | the column |
| `apps/api/app/schema/locale/read.py`, `apps/api/app/features/locales/` | read model |
| `openapi.schemas.json` | regenerated |
| `apps/web/src/services/localesApi.ts` | the field |
| `apps/discovery-ingest/tests/test_i18n_committed_locales.py`, `test_i18n_manifest.py` | honesty and literal tests |
| `apps/api/tests/test_enable_locale.py`, `test_locales_api.py` | enable and read tests |
| `docs/operations/locales.md` | acceptance paths |

## Red tests

**Happy path**
- `Enable · a machine_accepted locale at 100% coverage is enabled and marked machine_translated`
- `Enable · a reviewed locale is enabled with machine_translated false`
- `Manifest · machine_accepted with accepted_by and accepted_on validates`
- `Read · GET /api/v1/locales includes machine_translated`
- `Web · LocaleRow and its fixtures carry the field; the contract test passes`

**Negative path**
- `Enable · a machine status is refused, and the message names the three statuses`
- `Enable · a locale below 100% coverage is refused`
- `Manifest · machine_accepted without accepted_by or accepted_on fails validation`
- `Manifest · accepted_by naming an engine (azure-translator, llm, claude) fails the honesty test`
- `Migration · downgrade removes the column and upgrade restores it with false`

## Green

Start with the literal and the honesty test, since they define what may be written. Then the gate, the migration, the read model and the web type.

## Refactor gate

- `_review_problem` dispatches on the status through a small table. No new boolean parameter is introduced.
- The two literals stay in step by a test that compares them, rather than by a copy comment.
- House rules: about 100 lines per file, at most 3 parameters, no `Any`.

## Verification

```bash
cd apps/api
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_enable_locale.py tests/test_locales_api.py tests/test_openapi_snapshot.py
bash scripts/check_migrations.sh
.venv/bin/python -m scripts.export_openapi
cd ../discovery-ingest && .venv/bin/python -m pytest -q tests/test_i18n_committed_locales.py tests/test_i18n_manifest.py
cd ../web && npm test -- LocaleContext AppMenu contract
cd ../.. && ./ci.sh
```

## Out of scope

Flags, code labels and notes in the switcher (15), changing the five locales' statuses in the repo, any native-review process beyond the manifest.

## Operator steps after merge

For each of `tr ru uk pl ro`, the operator, not a tool, reviews enough of the strings to accept them. The operator then records `accepted_by` (the operator's name) and `accepted_on` (today's date) in the manifest, and runs `enable_locale.py` for that locale.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-14-machine-accepted
# test(api)/test(ingest): ... (red), feat(api): ... (green), feat(ingest): literal mirror, docs(ops): locales
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
