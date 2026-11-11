---
name: "Chapter 06 — Admin Translator coverage"
overview: "Show the Azure character meter as its own Translator section on the discovery coverage page, and add a per-locale card translation coverage table from a new read-only endpoint in the translation feature. Each piece loads independently, so a failure in one leaves the others visible."
id: AZ06
depends_on:
  - AZ01
  - AZ03
touches:
  - apps/api/app/features/translation/admin_controller.py
  - apps/api/app/features/translation/admin_service.py
  - apps/api/app/features/translation/admin_read.py
  - apps/api/app/schema/translation/admin.py
  - apps/api/app/features/translation/router.py
  - apps/api/app/features/translation/repository.py
  - apps/api/tests/
  - apps/web/src/features/discovery-admin/components/coverage/
  - apps/web/src/features/discovery-admin/containers/DiscoveryCoveragePage.tsx
  - apps/web/src/features/discovery-admin/utils/
  - apps/web/src/features/discovery-admin/types/
  - apps/web/src/hooks/
  - apps/web/src/services/discoveryAdminApi.ts
  - apps/web/src/app/queryKeys.ts
  - apps/web/src/i18n/fallback/
  - apps/api/scripts/seed_data/translations/
execution: chapter-implementer
---

# Chapter 06 — Admin Translator coverage

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Depends on:** [Chapter 01](01-ledger-resource.md), [Chapter 03](03-character-meter-and-floor.md) · **Decisions:** [D2](../gaps-and-decisions.md#d2--azure-ai-translator-f0-first-a-19-million-character-monthly-cap) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

The coverage page gains a Translator section with the monthly character meter, and a per-locale table of card translation status. The table comes from its own read-only endpoint, so the discovery coverage response does not depend on translation.

## Scope

- In: the translation admin endpoint for card rows, the Translator section, the per-locale table, the query, i18n keys, OpenAPI snapshot.
- Out: snapshot rows (chapter 12), a document-floor display (see the decision below), any write.

## Design

1. **Budget data.** The Translator section reads the budgets query the page already makes. The `azure_translator_chars` row supplies the cap, used, remaining, period and exhausted state. No new API is needed for the meter.
2. **Coverage endpoint.** `GET /api/v1/admin/translations/coverage`, in the translation feature: controller → service → repository. It returns, per target locale, counts of translated, stale, pending, claimed and failed card units, plus the denominator (candidates with a German card source). It reuses the grouped counts in `TranslationRepository.summary`. It is read-only.
3. **Guard.** The route uses the discovery admin guard tuple (`apps/api/app/features/discovery/guards.py`). The translation controller imports only that tuple, not any discovery service or repository.
4. **Decision: no floor marker.** The approved plan showed a card-band floor marker. This chapter does not, because the document share is a worker setting in GitHub Actions. Copying it into API settings would create two sources of truth. The runbook (chapter 16) documents the share and its effect.
5. **Web.** A `TranslatorBudget` section, built from `translatorBudgetOf` (in `utils/`), excluded from the generic table as neurons are. It shows used, cap, remaining, period, and an exhausted badge. A `TranslationCoverageTable` uses the shared `DataTable`, one row per locale. The page keeps two independent queries, so a failure in either leaves the other visible.
6. **Query keys.** Added to `app/queryKeys.ts`. Components never build query keys inline.

## Files

| Path | Change |
| --- | --- |
| `translation/admin_controller.py`, `admin_service.py`, `admin_read.py` (new) | route, service, read model |
| `schema/translation/admin.py` (new) | response schema |
| `translation/router.py` | mount the admin route |
| `translation/repository.py` | reuse grouped counts; add the candidate denominator |
| `apps/web/.../coverage/TranslatorBudget*.tsx` (new) | section and its parts, one component per file |
| `apps/web/.../coverage/TranslationCoverageTable.tsx` (new) | per-locale table on `DataTable` |
| `apps/web/.../utils/translatorBudget.ts` (new) | selects the resource row |
| `apps/web/.../containers/DiscoveryCoveragePage.tsx` | render the section and the table |
| `apps/web/src/hooks/`, `services/discoveryAdminApi.ts`, `app/queryKeys.ts` | query, service, key |
| `apps/web/src/i18n/fallback/*.json`, `apps/api/scripts/seed_data/translations/*.json` | section and column keys in seven locales |
| `openapi.schemas.json` | regenerated |

## Red tests

**Happy path**
- `API · coverage counts translated, stale, pending, claimed and failed per configured locale`
- `API · a locale with no rows still appears, with zeros`
- `API · the denominator counts candidates with a German card source`
- `Web · the Translator section shows used, cap, period and the remaining amount for azure_translator_chars`
- `Web · the table renders one row per locale on DataTable and passes the table accessibility helper`
- `Web · the coverage tables still render when the translation query fails`

**Negative path**
- `API · a caller outside the admin allowlist is refused`
- `API · the endpoint writes nothing and enqueues nothing`
- `Web · a missing azure row shows a "not configured" note and does not crash`
- `Web · coverageComposition still asserts the existing eight summary cards`

## Green

The smallest change for each red test. Keep the existing neuron table and its tests untouched.

## Refactor gate

- Each new component is one file of about 100 lines or fewer, with at most 3 props.
- `translatorBudgetOf` and `generalBudgetsOf` share one resource-selection helper; extract it when the second call appears.
- The admin controller holds no query logic; the service calls the repository; the repository holds the SQL.
- House rules: no inline query keys, no service calls from components, one nesting level.

## Verification

```bash
cd apps/api
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_translation_admin*.py tests/test_discovery_budgets_api.py
.venv/bin/python -m scripts.export_openapi
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_openapi_snapshot.py
cd ../web && npm test -- coverage TranslatorBudget TranslationCoverage && npm run typecheck && npm run lint
cd ../.. && ./ci.sh
```

## Out of scope

Snapshot coverage rows (12), the document floor display (see the decision), write endpoints, charts.

## Operator steps after merge

None.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-06-admin-translator
# test(api): ... (red), feat(api): ... (green), test(web): ..., feat(web): ..., refactor(web): ... (gate)
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
