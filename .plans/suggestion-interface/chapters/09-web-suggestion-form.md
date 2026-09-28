---
name: "Chapter 9 — Web suggestion form"
overview: "A protected /suggest page where a signed-in person proposes a new document: municipality, title, official URL, optional description and taxonomy tags; shows duplicate conflicts with links, and a Suggest entry in the menu."
todos:
  - id: api
    content: "suggestionsApi.createSuggestion and useCreateSuggestion"
    status: completed
  - id: form
    content: "SuggestionForm and its field components"
    status: completed
  - id: page
    content: "SuggestPage, protected route, menu entry, i18n"
    status: completed
isProject: false
---

# Chapter 9 — Web suggestion form

**Repo:** `redtape` (`apps/web`, i18n seeds in `apps/api/scripts/seed_data/translations`) · **Branch:** `feat/suggestions-web-form` · **Status:** implemented, PR open

**Depends on:** [5](05-human-submit-endpoint.md), auth [11](../../auth/chapters/11-web-menu-and-route-guard.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A signed-in person can suggest a document in under a minute and gets a clear result: accepted (with a link
to the new suggestion), a duplicate (with links to what exists), or a field error.

## Design decisions

**Feature slice `apps/web/src/features/suggestions/`** with the documents layout: `types/`, `services/`,
`hooks/`, `containers/`, `components/`.

**Reuse, do not rebuild.** The municipality comes from the existing `LocationPicker` /
`useLocationCascade` (yields `municipalityCode`, sent as `municipality_code`, D6); tags come from
`useDomainsQuery` and `useLifeSituationsQuery` (chip toggles as in `DocumentFilters`).

**Title language.** One title field, stored under the current UI locale key (`title_i18n[locale]`); a second
optional field lets the person add the other language. Rejected for now: a full locale tab set (only `de`
and `en` are enabled).

**Component tree (one per file):**

```
containers/SuggestPage.tsx        (RequireAuth is applied in routes; page owns submit state)
components/suggest/SuggestionForm.tsx
components/suggest/TitleFields.tsx
components/suggest/TaxonomyChips.tsx
components/suggest/ConflictList.tsx      (links to /documents/:id and /suggestions/:id)
components/suggest/SubmittedNotice.tsx   (link to the created suggestion)
```

**Validation** is client-side for the cheap rules (municipality chosen, title non-blank, URL starts with
`http://` or `https://`, ≤ 500 chars) and server-side for the rest; a 422 is mapped to field messages by
`parseFieldErrors(error)` (pure function, its own tests), a 409 to `ConflictList`.

**Route** `/suggest` lazy-loaded and wrapped in `<RequireAuth>`; menu gets **Suggest** above the account
item, visible to everyone (anonymous visitors are sent to login and back, auth chapter 11).

**i18n**: `suggest.*` keys (`title`, `municipality`, `document_title`, `document_title_other`, `official_url`,
`description`, `tags`, `submit`, `success_title`, `success_body`, `conflict_title`, `conflict_document`,
`conflict_suggestion`, `error_generic`) in fallback bundles and seeds, plus `nav.suggest`.

## Files

**Add** — `apps/web/src/features/suggestions/{types/index.ts, services/suggestionsApi.ts,
hooks/useCreateSuggestion.ts, containers/SuggestPage.tsx, components/suggest/*, utils/parseFieldErrors.ts}`,
tests beside each.

**Edit** — `apps/web/src/app/routes.tsx`, `apps/web/src/components/layout/AppMenu.tsx`,
`apps/web/src/i18n/fallback/{de,en}.json`, `apps/api/scripts/seed_data/translations/{de,en}.json`.

## Red tests

| Test | Asserts |
| --- | --- |
| `suggestionsApi · createSuggestion posts the payload with the bearer token` | Method, path, body |
| `suggestionsApi · a 409 surfaces conflicts on the error` | Typed error |
| `SuggestionForm · submits municipality_code, title under the current locale and URL` | Request body |
| `SuggestionForm · blocks submit without a municipality` | No request |
| `SuggestionForm · blocks a blank title` | Negative |
| `SuggestionForm · blocks a URL that is not http or https` | Negative pair |
| `SuggestionForm · includes selected domain and situation codes` | Body lists codes |
| `SuggestionForm · disables the submit button while sending` | State |
| `SuggestPage · shows the success notice with a link to the new suggestion` | Link href |
| `SuggestPage · shows conflicts with links to documents and suggestions on 409` | Two link kinds |
| `SuggestPage · maps a 422 field error onto the URL field` | Message next to field |
| `SuggestPage · a network failure shows the generic error and keeps the form values` | No data loss |
| `parseFieldErrors · maps Litestar validation extras to field names` | Pure |
| `routes · /suggest redirects an anonymous visitor to /login` | Guard applied |
| `AppMenu · shows Suggest for everyone` | Anonymous and signed in |
| `i18n · every suggest.* key exists in both fallback bundles` | Parity |

## Green

1. API service and hook; tests 1–2.
2. Form fields with validation; tests 3–8.
3. Page states and conflict list; tests 9–13.
4. Route, guard, menu, i18n; tests 14–16.

## Refactor gate

- `SuggestionForm` ≤ ~100 LOC by delegating fields to the small components above; no component owns more
  than one concern.
- `parseFieldErrors` is pure and separate from React.
- Report the outcome.

## Progress

All 16 red tests pass. Implementation landed in four green cycles matching the plan: (1)
`suggestionsApi`/`useCreateSuggestion`, (2) `SuggestionForm` and its field components, (3) `SuggestPage`
and its result components, (4) the route guard, menu entry and i18n keys.

Two deviations from the component tree as planned, both to keep `SuggestionForm` near the ~100 LOC gate:
the URL field and the municipality header+`LocationPicker` wrapper were each split into their own
components (`UrlField.tsx`, `MunicipalityField.tsx`), and `TaxonomyChips` grew its own `TaxonomyChipGroup`/
`TaxonomyChip` sub-components (mirroring `documents/.../document-filters/FilterGroup`+`FilterChip`, kept
local to this feature slice rather than importing across features). With those extractions,
`SuggestionForm` itself is ~100 LOC of state wiring and two pure helpers (`isValidUrl`, `buildTitleI18n`);
every field-specific concern lives in its own file. One extra i18n key beyond the plan's list,
`suggest.view_suggestion`, was needed for `SubmittedNotice`'s link text.

`parseFieldErrors` maps a Litestar `ValidationException` body's `extra: [{key, message, source}]` entries
(confirmed against `apps/api/app/_signature/model.py`'s `ErrorMessage` shape) to `{field: message}` by
taking the last `.`-segment of `key` (e.g. `payload.official_url` → `official_url`); it stays a pure
function over `ApiRequestError`, no React involved.

`createSuggestion` catches a 409 `ApiRequestError` and re-throws a typed `SuggestionConflictError` carrying
the parsed `conflicts` array (`extra.conflicts`, per the chapter 5 controller's `_to_http`); `SuggestPage`
branches on `mutation.error instanceof SuggestionConflictError` for the duplicate view and on
`ApiRequestError` + `status === 422` for field errors, falling back to a generic error notice — mirroring
`useMutation`'s built-in reset-on-retry so a corrected resubmit clears the previous error without extra
state.

**Found and fixed, out of `SuggestionForm`/`SuggestPage`'s own scope:** integration tests that walk
`LocationPicker`'s three cascading selects and then type into a later field were flaky — Ark UI's `Select`
restores focus to its trigger asynchronously on close, which could steal focus back mid-typing. Both test
files now wait for the trigger to regain focus after each selection before moving on; stable across
repeated runs.

**Found, not fixed (pre-existing, unrelated):** `AppMenu.test.tsx`'s `Escape closes and returns focus to
the burger` test is flaky when run scoped to a small file set (reliably reproduces on unmodified `main`
too, given the same "choosing a language…" test immediately before it) — some async focus-restore from
Chakra's nested `Menu` leaks past that test's `cleanup()`. It rarely surfaces in the full `npm test` run
(8/9 clean runs observed) and `./ci.sh` passed end to end, so it wasn't chased further here; worth a
dedicated look separately.

`./ci.sh` is green: apps/api pytest, ruff, mypy, migrations; apps/web lint, format:check, typecheck, test
(252 passed), build. `apps/api/scripts/seed_i18n.py` re-run cleanly. Manual browser verification (submit,
duplicate conflict, signed-out redirect, locale switch) was not performed in this session — no interactive
browser was available — and should be done before or shortly after merge.

Commits on `feat/suggestions-web-form`:
1. `test(web): describe posting a suggestion and its 409 conflict shape` /
   `feat(web): add createSuggestion and useCreateSuggestion for the suggestions API`
2. `test(web): describe the suggestion form's fields, validation and codes` /
   `feat(web): add SuggestionForm and its field components, and suggest.* i18n keys`
3. `test(web): describe the suggestion page's success, conflict and error states` /
   `feat(web): add SuggestPage with conflict, success and field-error handling`
4. `test(web): describe the /suggest route guard and menu entry` /
   `feat(web): wire /suggest behind RequireAuth and add the Suggest menu item`

## Verification

```bash
cd apps/web
npm run test -- src/features/suggestions src/components/layout src/i18n
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
cd apps/api && python scripts/seed_i18n.py
```

Manual (API and Supabase running): submit a suggestion; submit it again and see the conflict links; sign out
and open `/suggest`, confirm the login redirect and return; switch to `de`.

## Out of scope

Requirement-edge suggestion UI (an action on the document detail page, seam in
[gaps](../gaps-and-decisions.md)), federal or state-level documents (municipality only, D6 seam), draft
saving.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-web-form
```

```text
test(web): describe the suggestion form, conflicts and route guard

feat(web): add the protected suggestion form and menu entry
```
