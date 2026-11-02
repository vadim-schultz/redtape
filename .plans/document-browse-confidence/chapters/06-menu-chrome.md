---
name: "Chapter 6 — Menu chrome"
overview: "Centre the Home button, close the menu when a menu item is clicked, and unlink the suggestion UI (menu link, route, page and form)."
todos:
  - id: centre-home
    content: "HomeMenuButton centred"
    status: pending
  - id: close-on-select
    content: "One delegated onClick on Menu.Content closes on a link or sign-out click"
    status: pending
  - id: unlink-suggest
    content: "Remove the menu link, the /suggest route, SuggestPage, SuggestView, useCreateSuggestion and nav.suggest"
    status: pending
  - id: tests
    content: "Close-on-select tests and updated menu/route tests"
    status: pending
isProject: false
---

# Chapter 6 — Menu chrome

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/document-browse-confidence-menu-chrome` · **Status:** planned
**Depends on:** none (placed before chapter 7: both edit `DocumentsMenuRow.tsx`) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

Three small, separate fixes in the app menu, each its own commit. Paths under `apps/web/src/`.

## Design

### (a) Centre the Home button

`components/layout/menu/HomeMenuButton.tsx:12` is `<Button asChild justifyContent="flex-start" variant="ghost" w="full">`. Change `justifyContent` to `"center"`. The ghost button already lays its content out as a flex row, so the icon and label centre as a pair. Keep `w="full"` (the parent `VStack` is `align="stretch"`); if a compact button is preferred, drop `w="full"` and add `alignSelf="center"`, but the full-width centred bar matches the panel. Add `HomeMenuButton.test.tsx` (none exists).

### (b) Close the menu when an item is clicked

Root cause: the links are plain elements, not Chakra `Menu.Item`s, so the Ark `closeOnSelect` (zag `ITEM_CLICK`) never fires; and `AppMenu` is mounted once above the router outlet (`AppBootstrap.tsx:27-29`), so its `open` state survives navigation. The language row only closes because `LanguageMenuRow` calls an explicit `onLocaleSelected`.

Fix in `components/layout/AppMenu.tsx`: add `onClick` on `Menu.Content` that sets `open` to `false` when `event.target` is inside an `a[href]` or the sign-out button:

```tsx
const closesMenu = (target: EventTarget) =>
  target instanceof Element && target.closest("a[href], [data-closes-menu]") !== null;
```

Mark the sign-out button in `menu/ProfileMenuRow.tsx` with `data-closes-menu`. Clicks on the colour switch (a `Switch.Root`) and on plain text do not match, so colour mode keeps the menu open (frontend-ui-menu D4). The extraction keeps the handler a one-liner (5-line limit). **Do not** wrap links in `Menu.Item asChild`: it puts `role="menuitem"` on the anchors and breaks every `getByRole("link", …)` test. The alternative of threading `onCloseMenu` through `DocumentsMenuRow`, `MenuIconLink` and `DiscoveryAdminMenuLinks` touches many files and the 3-props rule; the delegate covers the discovery admin links too, with no per-link code.

### (c) Unlink the suggestion UI

There is no suggestion dialog: the UI is the `/suggest` page and one menu icon link (D3).

- `components/layout/menu/DocumentsMenuRow.tsx:22` remove `<MenuIconLink Icon={FaArrowUp} label={t("nav.suggest")} to="/suggest" />`, the `FaArrowUp` import (line 2) and fix the doc comment at line 10.
- `app/routes.tsx`: remove the `/suggest` route (lines ~81-90), the lazy `SuggestPage` import, and `RequireAuth` if no other route uses it (check before removing). Keep `/suggestions` and `/suggestions/:id`.
- Delete `features/suggestions/containers/SuggestPage.tsx` and its test, `features/suggestions/components/SuggestView/` (whole folder, includes `SuggestionForm`, `TaxonomyChips`, `MunicipalityField`, …), `hooks/useCreateSuggestion*`, and `createSuggestion` in `services/suggestionsApi.ts` (and its test) if nothing else uses it. Keep `formatRelativeTime` and everything the list/detail pages and the discovery-admin panel import. Before deleting `parseFieldErrors`, `useSuggestionError` and similar helpers, grep for other importers.
- i18n: remove `nav.suggest` from `i18n/fallback/en.json`, `de.json` and `apps/api/scripts/seed_data/translations/en.json`, `de.json`. Leave the `suggest.*` and `suggestions.*` namespaces (parity tests need them non-empty; `useCountLabel.test.tsx` reads `suggestions.count_*`).

## Tests

Happy path:
- `AppMenu.test.tsx`: clicking Home, a Documents-row link, a profile `/login` link and a discovery admin link (admin probe 200) each closes the menu (`queryByRole("menu")` is gone); clicking Sign out closes it; the language flag still closes it.
- `HomeMenuButton.test.tsx`: the button content is centred (`justify-content: center` through `emotionRules`) and links to `/`.

Negative path:
- Toggling the colour mode switch keeps the menu open (existing test at `AppMenu.test.tsx:126-138` stays green).
- Clicking the panel's plain label text does not close it.
- `/suggest` now renders the not-found view (replace `App.test.tsx:79-86`, which asserted a redirect to `/login`); `/suggestions/:id` still renders without auth (`App.test.tsx:88-96`).

Update the tests that assert the removed link: `AppMenu.test.tsx` (≈266-279, 301-304, 343) and `DocumentsMenuRow.test.tsx` (counts 7 → 6 and 3 → 2, the label list at ≈99-110, the candidates row at ≈119-122).

## Verification

```bash
cd apps/web && npx vitest run src/components/layout src/app src/features/suggestions src/i18n
./ci.sh
```

## Refactor gate

Scan `AppMenu.tsx` (Message Chains on the event target → the small `closesMenu` function), `AppMenuPanel.tsx` and `DocumentsMenuRow.tsx`. Confirm `architecture.test.ts` still passes.

## Commits

- `fix(web): centre the Home button in the app menu`
- `fix(web): close the app menu when a menu item is clicked`
- `refactor(web): unlink the suggestion form from the menu and routes`

## Out of scope

The `/suggestions` list and detail pages; the suggestion API and voting; closing the menu on colour-mode toggle; the `/candidates` menu link (chapter 7). Update `.plans/frontend-ui-menu/00-architecture.md`, which still lists `/suggest` as a documents-row link (one-line note), in this chapter's docs commit.
