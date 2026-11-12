---
name: "Chapter 13 — Web document accordion"
overview: "Add a collapsed Document contents item to the candidate detail accordion. It shows the procedure page in the interface language, with loading, pending, skipped, error, stale and truncated states, and is hidden in German. The query runs only when the item is opened."
id: AZ13
depends_on:
  - AZ12
touches:
  - apps/web/src/features/candidates/components/CandidateDetailView/CandidateDetailContent.tsx
  - apps/web/src/features/candidates/components/DocumentTranslationSection/
  - apps/web/src/hooks/useDocumentTranslationQuery.ts
  - apps/web/src/services/documentTranslationApi.ts
  - apps/web/src/types/documentTranslation.ts
  - apps/web/src/app/queryKeys.ts
  - apps/web/src/test/candidatesApiStub.ts
  - apps/web/src/test/contract/
  - apps/web/src/i18n/fallback/
  - apps/api/scripts/seed_data/translations/
execution: chapter-implementer
---

# Chapter 13 — Web document accordion

**Repo:** `redtape` (`apps/web`, plus seed data) · **Depends on:** [Chapter 12](12-snapshot-read-api.md) · **Decisions:** [D7](../gaps-and-decisions.md#d7--eager-queue-driven-translation-reads-never-translate) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

On `/candidates/:id`, a collapsed "Document contents" item shows the translated procedure page in the interface language. It fetches only when opened, follows the locale switch, and is absent in German.

## Scope

- In: the accordion item, the section component and its parts, hook, service, type, query key, states, keys in seven locales, the contract map, tests.
- Out: the API (12), the card popover (already exists), changing the default open items.

## Design

1. **Accordion item.** Added to the wrapper in `CandidateDetailContent.tsx` with value `"document"`. It is not in the default-open list (`ingress`, `egress`, `flow`). It is absent when the interface locale is `de`.
2. **Section component** (`DocumentTranslationSection/`, one component per file, barrel `index.ts`):
   - `DocumentTranslationSection` picks the state and renders one of the parts.
   - `DocumentBlocks` maps block kinds to Chakra components: `h1`–`h6` → `Heading`, `p` → `Text`, `li` → `List.Item`, `row` → a simple grid of cells, `dt` → bold `Text`. An untranslated block gets `lang="de"`.
   - `DocumentStateNote` renders pending, skipped, stale and truncated notes.
   - The machine-translation note and a source link (`rel="noopener noreferrer"`, `target="_blank"`) appear with ready content.
3. **Lazy fetch.** The query is enabled only while the item is open. Collapsing and reopening does not refetch within the stale time.
4. **Hook and service.** `useDocumentTranslationQuery` lives in `hooks/` and calls `documentTranslationApi` in `services/`. The query key comes from `app/queryKeys.ts` as `candidates.documentTranslation(id, locale)`. Components never call the service.
5. **Locale.** The locale comes from `LocaleContext`. A switch invalidates every query already, so the section refetches for the new locale.
6. **Error and retry.** A failed request shows the existing error component with a retry action. A 404 with a code shows the matching note, not the error.
7. **Unknown block kinds** are dropped with no crash.
8. **Strings.** Keys for the notes, the item title and the machine note are written to all seven seed files and mirrored to the web fallbacks. `fallback.test.ts` lists them.
9. **Contract.** `contract.test.ts` gets the field map for the new response type, as the other types do.

## Files

| Path | Change |
| --- | --- |
| `candidates/components/CandidateDetailView/CandidateDetailContent.tsx` | the new accordion item |
| `candidates/components/DocumentTranslationSection/*.tsx` (new) | section, blocks, notes, one per file |
| `hooks/useDocumentTranslationQuery.ts` (new) | query |
| `services/documentTranslationApi.ts` (new) | request |
| `types/documentTranslation.ts` (new) | response types |
| `app/queryKeys.ts` | the key |
| `test/candidatesApiStub.ts` | a stub for the document route |
| `test/contract/` | field map |
| `i18n/fallback/*.json`, `apps/api/scripts/seed_data/translations/*.json` | keys in seven locales |

## Red tests

**Happy path**
- `Accordion · the document item is collapsed and not in the default-open list`
- `Lazy · no document request before the item is opened; one request after`
- `Ready · blocks render in order, with lang set on untranslated blocks`
- `Ready · the machine note and the source link appear with the content`
- `Locale · a switch to another locale refetches for that locale`
- `Accessibility · the trigger is keyboard operable and the target is at least 44 px`

**Negative path**
- `Accordion · the item is absent when the interface locale is de`
- `States · loading shows a skeleton with role status and aria-busy`
- `States · 404 translation_pending shows the pending note, not the error`
- `States · 404 skipped shows the skip reason`
- `States · a 503 shows the error with a retry that refetches`
- `States · stale and truncated each show their note with the content`
- `Blocks · an unknown block kind is dropped without crashing`
- `Contract · the field map matches the API schema`

## Green

Implement the item and the not-found states first, then the ready blocks, then the locale and retry behaviour.

## Refactor gate

- Each component is one file, about 100 lines or fewer, with at most 3 props.
- The block mapping is a table from kind to component; no switch with more than two branches.
- No inline query keys, no service calls from components, no physical CSS properties where logical ones exist.
- House rules: one nesting level, no boolean flags for variants (use the `state` union).

## Verification

```bash
cd apps/web
npm test -- DocumentTranslation CandidateDetail fallback parity contract
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

## Out of scope

The API, the card popover, default-open changes, an "all mentioning pages" view, right-to-left layout.

## Operator steps after merge

None.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-13-web-document
# test(web): ... (red), feat(web): ... (green), refactor(web): ... (gate), feat(api): seed keys
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
