---
name: "Chapter 17 — Translation read path and pop-over"
overview: "Serve the stored translation for the reader's language on candidate cards and details, and show it in an accessible pop-over beside the original text, with no live translation and no extra request."
id: C17
depends_on:
  - C10
  - C13
touches:
  - apps/api/app/features/candidates/
  - apps/api/app/schema/candidate/
  - apps/api/tests/
  - apps/web/src/features/documents/
  - apps/web/src/features/candidates/
  - apps/web/src/i18n/fallback/
  - apps/web/src/test/contract/
execution: chapter-implementer
todos:
  - id: api-read
    content: "Add the stored translation for the request locale to candidate cards and details with one batched lookup."
    status: pending
  - id: stale-flag
    content: "Flag translations whose German source has changed since they were made."
    status: pending
  - id: popover
    content: "Add the TranslationPopover component with a language trigger on cards and the detail view."
    status: pending
  - id: copy
    content: "Add the pop-over copy for en and de."
    status: pending
  - id: tests
    content: "Add API, query-count, component, accessibility and no-network tests."
    status: pending
---

# Chapter 17 — Translation read path and pop-over

**Repo:** `redtape` (`apps/api`, `apps/web`)
**Depends on:** [Chapter 10](10-results-presentation.md), [Chapter 13](13-translation-schema-and-core.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Let a reader who does not read German see what a document is about, without replacing the original and without a live translation call: the stored, machine-made translation appears in a pop-over next to the German text.

## Design decisions

- **The original stays primary.** Cards and details keep showing the German title and description. The translation is secondary, opened on demand, and always labelled as machine translated.
- **API.** Candidate cards (list) and the candidate detail gain `translation`: `{locale, title, description, source: "mt" | "human", stale: boolean}` or `null`. It is present only when the request locale is not `de` and a `candidate_translation` row exists for it. `stale` is true when the stored `source_hash` differs from the hash of the current German title and description (chapter 13's function; both inputs are already at hand in `card_builder.py`).
- **No N+1.** The list service already hydrates tags and descriptions for the page in batches; add one batched `translations_for(candidate_ids, locale)` query to that hydration. A test asserts the query count does not grow with page size.
- **No live work.** Opening the pop-over performs no request: the data arrived with the list response. Nothing in the API or UI calls a model at read time.
- **Contract.** The OpenAPI snapshot and the web contract fixture are regenerated; clients that do not know the field keep working.
- **Web `TranslationPopover`** (`features/documents/components/TranslationPopoverView/`, at most 3 props: `translation`, `lang`, `label`), built on Chakra v3 `Popover`:
  - trigger: a small ghost `IconButton` with a language icon (`LuLanguages`), `aria-label` from `documents.translation_open`, minimum 44 px touch target; rendered only when `document.translation` exists (never for `de`, never when absent);
  - content: the translated title as a heading and the description, each with `lang` set to the translation's locale so screen readers and hyphenation behave, a note ("Machine translation, may contain errors. The German original is authoritative.") and, when `stale`, a second note that the original has changed since;
  - behaviour: opens on click, Enter and Space; closes on Escape or outside click and returns focus to the trigger; maximum width about 360 px, scrolls for long text; flips to stay on screen at phone width.
  - placement: beside the title in the card header and the detail header, **outside** the card's link so there are no nested interactive elements (taxonomy suite D8); the translation does not navigate.
- `DocumentSummary` and the candidate detail types gain `translation`; `documentMapper.ts` maps it; the detail view reuses the same component.
- Copy for `en` and `de` is added here; chapter 11 translates it with the rest of the interface (it runs after this chapter for that reason).
- Respect `apps/web/CLAUDE.md`: about 100 lines per file, about 3 props, layering enforced by `architecture.test.ts`.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/candidates/service.py`, `card_builder.py`, `repository/` | Batched translation lookup and `translation` assembly with the stale flag. |
| `apps/api/app/schema/candidate/read.py` | `CandidateTranslation`, `translation` on card and detail. |
| `apps/api/tests/test_candidates_translation_api.py` | API behaviour and query count. |
| `apps/api/tests/test_openapi_snapshot.py`, `apps/web/src/test/contract/openapi.schemas.json` | Regenerate. |
| `apps/web/src/features/documents/components/TranslationPopoverView/` | `TranslationPopover.tsx`, `index.ts`, test. |
| `apps/web/src/features/documents/components/DocumentsListView/DocumentCard.tsx` and the candidate detail header | Place the trigger. |
| `apps/web/src/features/candidates/types/index.ts`, `features/documents/types/index.ts`, `services/documentMapper.ts` | Types and mapping. |
| `apps/web/src/i18n/fallback/en.json`, `de.json` | `documents.translation_open`, `translation_machine_note`, `translation_stale_note`. |

## Red tests

### Happy path

- `api · a Turkish reader gets the stored translation on list and detail`; a German reader gets `null`.
- `api · stale is true after the German description changes`; `source` reflects `human` rows.
- `api · the list issues a constant number of queries regardless of page size`.
- `popover · the trigger appears only when a translation exists and opens the translated title and description`.
- `popover · sets lang on the translated content and shows the machine-translation note` (and the stale note when flagged).
- `popover · opens without any network request` (fetch spy asserts zero calls).
- `popover · keyboard: Enter and Space open, Escape closes and focus returns to the trigger`.
- `contract · responses without the new field still parse`.

### Negative path

- `api · no translation row means null, not an error or a live translation`.
- `api · a locale without a stored translation never falls back to another locale's text`.
- `popover · absent for locale de and when translation is null`.
- `card · the trigger is not inside the card link` (no nested interactive elements).
- `popover · very long text scrolls inside the content and does not overflow the viewport`.

## Green

1. API hydration, stale flag, DTO; regenerate the contract.
2. Types, mapper and component; place the trigger in the card and detail headers.
3. Check desktop and phone width in the browser with a forced `tr` and `ru` locale and long text.

## Refactor gate

- Translation assembly lives in one function; the card builder does not recompute hashes inline.
- The batched lookup shares the existing page hydration, not a second pass.
- The component has a typed props interface, tokens only, no inline styles; no duplicated popover markup between card and detail.
- Architecture test passes; no component imports a feature service.

## Verification

```bash
cd apps/api
uv run pytest tests/test_candidates_translation_api.py tests/test_candidates_public_api.py tests/test_openapi_snapshot.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../web
npm test -- src/features/documents src/features/candidates src/test/contract
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Record screenshots (card with trigger, open pop-over, stale note, phone width, `tr` and `ru`) and the query-count test result in [../run-ledger.md](../run-ledger.md).

## Out of scope

Producing translations (chapters 13 to 15), replacing the German text with the translation, a language picker inside the pop-over, user-submitted corrections, translating the pop-over copy (chapter 11).

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/translation-popover
```

```text
test(api): describe stored translations on candidate reads
feat(api): serve the stored translation for the request locale
test(web): describe the translation pop-over
feat(web): show the machine translation in a pop-over beside the original
```
