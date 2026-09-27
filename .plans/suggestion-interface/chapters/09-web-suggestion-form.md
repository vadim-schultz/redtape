---
name: "Chapter 9 — Web suggestion form"
overview: "A protected /suggest page where a signed-in person proposes a new document: municipality, title, official URL, optional description and taxonomy tags; shows duplicate conflicts with links, and a Suggest entry in the menu."
todos:
  - id: api
    content: "suggestionsApi.createSuggestion and useCreateSuggestion"
    status: pending
  - id: form
    content: "SuggestionForm and its field components"
    status: pending
  - id: page
    content: "SuggestPage, protected route, menu entry, i18n"
    status: pending
isProject: false
---

# Chapter 9 — Web suggestion form

**Repo:** `redtape` (`apps/web`, i18n seeds in `apps/api/scripts/seed_data/translations`) · **Branch:** `feat/suggestions-web-form` · **Status:** planned

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
