---
name: "Chapter 17 — Translation read path and pop-over"
overview: "Mark candidates that have a stored translation for the reader's language, serve the stored text from object storage on demand, and show it in an accessible pop-over beside the original text, with no live translation."
id: C17
depends_on:
  - C10
  - C13
touches:
  - apps/api/app/features/candidates/
  - apps/api/app/features/translation/
  - apps/api/app/schema/candidate/
  - apps/api/tests/
  - apps/web/src/features/documents/
  - apps/web/src/features/documents/hooks/
  - apps/web/src/features/candidates/
  - apps/web/src/i18n/fallback/
  - apps/web/src/test/contract/
execution: chapter-implementer
todos:
  - id: api-read
    content: "Add a translation summary (locale, source, stale) to candidate cards and details with one batched index lookup."
    status: pending
  - id: text-endpoint
    content: "Add the stored-text endpoint that reads the translation object from R2 with ETag revalidation."
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
- **API, summary.** Candidate cards (list) and the candidate detail gain `translation`: `{locale, source: "mt" | "human", stale: boolean}` or `null`. It carries availability and provenance only, no text. It is present only when the request locale is not `de` and a `candidate_translation` index row exists for it. `stale` is true when the row's `source_hash` differs from the hash of the current German title and description (chapter 13's function; both inputs are already at hand in `card_builder.py`).
- **API, stored text.** `GET /api/v1/candidates/{candidate_id}/translation?locale=<code>` (the locale defaults to the resolved request locale) looks up the index row, answers `404` when none exists or the locale is `de`, then reads the object through `TranslationStore` and returns `{locale, title, description, source, stale, engine}`. The `ETag` is derived from `content_sha256` (the helpers the screenshot route uses, `candidates/etag.py`); a matching `If-None-Match` answers `304` **without touching the store**; `Cache-Control` is short (`max-age` of a few hours with revalidation, not `immutable`, because a re-translation replaces the content at the same URL). Object storage not configured → `503`; an index row whose object is missing → `404` with a logged inconsistency. The route is on the public read router, rate limited like the other public reads, and every read is a metered Class B operation.
- **No N+1.** The list service already hydrates tags and descriptions for the page in batches; add one batched `translations_for(candidate_ids, locale)` query over the index rows to that hydration. A test asserts the query count does not grow with page size and that a list page makes **zero** object-store calls.
- **No live work.** Nothing in the API or UI calls a model at read time. Opening the pop-over for the first time reads one stored object (decision D17); later opens come from the client cache, and a revalidation is a `304`.
- **Contract.** The OpenAPI snapshot and the web contract fixture are regenerated; clients that do not know the field keep working.
- **Web `TranslationPopover`** (`features/documents/components/TranslationPopoverView/`, at most 3 props: `candidateId`, `summary`, `label`), built on Chakra v3 `Popover`, with a `useCandidateTranslationQuery(candidateId, locale, enabled)` hook in `features/documents/hooks/` on the existing TanStack Query layer (fetches only once the pop-over has been opened; a few minutes of `staleTime`; one retry):
  - trigger: a small ghost `IconButton` with a language icon (`LuLanguages`), `aria-label` from `documents.translation_open`, minimum 44 px touch target; rendered only when `document.translation` exists (never for `de`, never when absent);
  - content: a compact loading state while the stored text loads; then the translated title as a heading and the description, each with `lang` set to the translation's locale so screen readers and hyphenation behave, a note ("Machine translation, may contain errors. The German original is authoritative.") and, when `stale`, a second note that the original has changed since; on failure a short message with a retry button (the German original stays visible either way);
  - behaviour: opens on click, Enter and Space; closes on Escape or outside click and returns focus to the trigger; maximum width about 360 px, scrolls for long text; flips to stay on screen at phone width.
  - placement: beside the title in the card header and the detail header, **outside** the card's link so there are no nested interactive elements (taxonomy suite D8); the translation does not navigate.
- `DocumentSummary` and the candidate detail types gain the `translation` summary; `documentMapper.ts` maps it; the detail view reuses the same component.
- Copy for `en` and `de` is added here; chapter 11 translates it with the rest of the interface (it runs after this chapter for that reason).
- Respect `apps/web/CLAUDE.md`: about 100 lines per file, about 3 props, layering enforced by `architecture.test.ts`.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/candidates/service.py`, `card_builder.py`, `repository/` | Batched index lookup and `translation` summary assembly with the stale flag. |
| `apps/api/app/features/translation/read_service.py`, `app/features/candidates/router.py` | Stored-text read through `TranslationStore`, ETag handling, the route. |
| `apps/api/app/schema/candidate/read.py` | `CandidateTranslationSummary`, `CandidateTranslationText`; `translation` on card and detail. |
| `apps/api/tests/test_candidates_translation_api.py`, `test_candidate_translation_text.py` | Summary behaviour, query count, stored-text route, ETag and `304`. |
| `apps/api/tests/test_openapi_snapshot.py`, `apps/web/src/test/contract/openapi.schemas.json` | Regenerate. |
| `apps/web/src/features/documents/components/TranslationPopoverView/` | `TranslationPopover.tsx`, `index.ts`, test. |
| `apps/web/src/features/documents/hooks/useCandidateTranslationQuery.ts` | Query hook, enabled on first open. |
| `apps/web/src/features/documents/components/DocumentsListView/DocumentCard.tsx` and the candidate detail header | Place the trigger. |
| `apps/web/src/features/candidates/types/index.ts`, `features/documents/types/index.ts`, `services/documentMapper.ts` | Types and mapping. |
| `apps/web/src/i18n/fallback/en.json`, `de.json` | `documents.translation_open`, `translation_machine_note`, `translation_stale_note`. |

## Red tests

### Happy path

- `api · a Turkish reader gets the translation summary on list and detail`; a German reader gets `null`.
- `text route · returns the stored title and description read from the object store, with an ETag`; a matching `If-None-Match` answers `304` and performs no store read.
- `api · stale is true after the German description changes`; `source` reflects `human` rows.
- `api · the list issues a constant number of queries regardless of page size and makes no object-store call`.
- `popover · the trigger appears only when a translation exists and opens the translated title and description`.
- `popover · sets lang on the translated content and shows the machine-translation note` (and the stale note when flagged).
- `popover · the first open requests the stored text once, shows loading then content; a second open makes no request` (fetch spy); no request happens before the first open.
- `popover · keyboard: Enter and Space open, Escape closes and focus returns to the trigger`.
- `contract · responses without the new field still parse`.

### Negative path

- `api · no translation row means null, not an error or a live translation`.
- `text route · 404 without a row or for de; 503 when object storage is not configured; 404 when the object is missing`.
- `popover · a failed fetch shows the retry message and keeps the German original visible`.
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

Record screenshots (card with trigger, loading and open pop-over, stale note, error state, phone width, `tr` and `ru`), the query-count result, and the R2 reads observed for one open and one revalidation in [../run-ledger.md](../run-ledger.md).

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
