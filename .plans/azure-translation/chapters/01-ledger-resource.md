---
name: "Chapter 01 — Azure character ledger resource"
overview: "Add the monthly ledger resource azure_translator_chars, so the API counts and caps Azure characters, the admin budget route lists it and the ingest worker accepts its name. Nothing reserves it until chapter 03."
id: AZ01
depends_on: []
touches:
  - apps/api/app/features/discovery/budget_resources.py
  - apps/api/app/config.py
  - apps/api/.env.example
  - apps/api/tests/
  - apps/api/tests/fixtures/discovery_machine_contract.json
  - apps/api/scripts/seed_data/translations/
  - apps/discovery-ingest/discovery_ingest/budget_models.py
  - apps/discovery-ingest/tests/
  - apps/web/src/i18n/fallback/
  - docs/operations/deployment-checklist.md
  - docs/operations/scheduled-jobs.md
  - .plans/azure-translation/
execution: chapter-implementer
---

# Chapter 01 — Azure character ledger resource

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`, `apps/web`, `docs/operations`) · **Depends on:** none · **Decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md) (D2) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Add the monthly resource `azure_translator_chars` to the shared budget ledger, with a cap the API and the admin page can read. No engine uses it yet: the meter and the adapter arrive in chapters 02 and 03.

## Scope

- In: the resource enum and spec, its cap setting, the ingest literal, the machine contract fixture, the generic admin label, docs and their tests.
- Out: any meter, adapter, floor or document share (chapter 03), the Translator section (chapter 06), the workflow (chapter 05).
- The ledger's `resource` column is `String(40)`, so no migration is needed.

## Design

1. `BudgetResource` gains `azure_translator_chars`. Its `RESOURCE_SPECS` entry uses `MONTHLY_PERIOD` and takes its cap from `Settings.budget_azure_translator_chars_monthly`.
2. The setting defaults to `1_900_000`, which is 95% of the F0 monthly allowance. It is read from `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY`, next to the other `budget_*` fields in `apps/api/app/config.py`.
3. The ingest `BudgetResource` literal in `budget_models.py` gains the same name. `BUDGET_RESOURCES` derives from it.
4. `BudgetRead.resource` is a plain string, so the OpenAPI snapshot does not change. The machine contract fixture does change and is regenerated.
5. The generic "Free-tier budgets" table already shows every resource except neurons. Its label is `discovery_admin.artifacts.budget_azure_translator_chars`, written to all seven seed files and mirrored byte-for-byte into the web fallbacks. The key also goes in `ARTIFACT_KEYS` in `fallback.test.ts`.
6. Docs: the deployment checklist says the budgets route "returns five resources" and lists the caps. Both change to six. The scheduled-jobs ledger table gains the row.

**Ship order hazard:** an old worker whose literal lacks the name fails validation when the API lists the new row. `BudgetGuard` then treats the whole ledger as unavailable, and `translate drain` exits 1. Ship the ingest literal in the same change as the API, or first.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/budget_resources.py` | `BudgetResource` member and `RESOURCE_SPECS` entry (monthly) |
| `apps/api/app/config.py` | `budget_azure_translator_chars_monthly` (env `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY`, default `1_900_000`) |
| `apps/api/.env.example` | commented default |
| `apps/discovery-ingest/discovery_ingest/budget_models.py` | the name in the `BudgetResource` literal |
| `apps/api/tests/fixtures/discovery_machine_contract.json` | regenerated with `scripts/export_machine_contract.py` |
| `apps/api/tests/test_budget_caps_ratio.py` | `ALLOWANCES` row: 2,000,000 a month |
| `apps/api/tests/test_discovery_budgets.py`, `test_discovery_budgets_api.py`, `test_discovery_operations_runbook.py` | the resource in the expected sets and `_CAP_DEFAULTS` |
| `apps/api/scripts/seed_data/translations/{de,en,tr,ru,uk,pl,ro}.json` | key `discovery_admin.artifacts.budget_azure_translator_chars` |
| `apps/web/src/i18n/fallback/{de,en,tr,ru,uk,pl,ro}.json` | byte-for-byte mirrors |
| `apps/web/src/i18n/fallback/fallback.test.ts` | key in `ARTIFACT_KEYS` |
| `docs/operations/deployment-checklist.md`, `docs/operations/scheduled-jobs.md` | six resources; ledger table row |

## Red tests

Write these first, and confirm each fails for the intended reason.

**Happy path**
- `API · budget snapshot lists azure_translator_chars with a monthly period and the configured cap`
- `API · the cap follows BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY`
- `API · a reserve is granted up to the cap and denied past it for azure_translator_chars`
- `Ingest · the BudgetRow literal accepts azure_translator_chars`
- `Contract · the committed machine fixture lists the new resource`
- `Web · the free-tier table labels the resource with its translated name`

**Negative path**
- `API · an unknown resource name still answers 404`
- `API · the OpenAPI snapshot is unchanged, because the resource field is a string`
- `Web · a missing translation key shows the raw resource name`
- `Contract · a stale fixture fails the contract test`

## Green

The smallest change for each red test: one enum member, one spec entry, one setting, one literal entry, one fixture regeneration, one key in seven bundles and their mirrors, and the docs sentences.

## Refactor gate

- `RESOURCE_SPECS` stays the single registry. Tests read it, and nothing copies its names.
- `budgets.py` gets no new branch.
- Keep new key lists in the existing `ARTIFACT_KEYS` block, not in a second list.
- House rules: about 5 lines per function, about 100 per file, no `Any`.

## Verification

```bash
cd apps/api
.venv/bin/python -m pytest -q tests/test_discovery_budgets.py tests/test_discovery_budgets_api.py tests/test_budget_caps_ratio.py tests/test_machine_contract_fixture.py tests/test_openapi_snapshot.py tests/test_discovery_operations_runbook.py
.venv/bin/python -m scripts.export_machine_contract   # the fixture diff must be the new enum value only
cd ../discovery-ingest
.venv/bin/python -m pytest -q tests/test_budget_guard.py tests/test_api_contract.py
cd ../web && npm test -- BudgetMeters fallback
cd ../.. && ./ci.sh
```

No migration is added, so `scripts/check_migrations.sh` is unchanged.

## Out of scope

Meter, floor, adapter, workflow, probe, Translator section, document share.

## Operator steps after merge

None, except that Render variable `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY` is set only if a non-default cap is wanted.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull   # the chief creates it from main if absent
git checkout -b feat/azure-01-ledger-resource
# test(api): ... (red), feat(api): ... (green), test(ingest): ..., feat(ingest): ..., feat(web): ..., docs(ops): ...
git push -u origin HEAD
# PR into feat/plans-azure-translation, never into main
```

End commit messages and the PR body with the attribution lines the session provides.
