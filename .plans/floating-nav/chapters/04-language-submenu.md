---
name: "Chapter 4 — Language submenu"
overview: "Rebuild the locale switcher as a Chakra Menu submenu listing available languages with the active one checked, keeping the existing locales query and loading/error behaviour."
todos:
  - id: submenu
    content: "LocaleSubmenu using nested Menu.Root and Menu.TriggerItem"
    status: pending
  - id: states
    content: "Loading placeholder and error omission preserved"
    status: pending
  - id: cleanup
    content: "Remove the ark Select usage"
    status: pending
isProject: false
---

# Chapter 4 — Language submenu

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/floating-nav-language-submenu` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §2, §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Language selection lives in the menu as a sub-menu, following the
[Chakra submenu pattern](https://chakra-ui.com/docs/components/menu#submenu).

## Design decisions

**Submenu structure.** A nested `Menu.Root` inside the parent menu, opened by `Menu.TriggerItem` labelled
with `common.language` and the current locale's flag; children are `Menu.ItemGroup` with
`Menu.RadioItem`-style items (flag + name), the active one carrying an `Menu.ItemIndicator` check.
Selecting calls `setLocale` from [LocaleContext](../../../apps/web/src/contexts/LocaleContext.tsx) and closes
the whole menu.

**Data.** Reuse the existing `["locales"]` query from
[LocaleSwitcher.tsx](../../../apps/web/src/components/layout/LocaleSwitcher.tsx); extract it to a small
`useLocalesQuery` hook if that keeps files under the size limit.

**States.** Loading: a disabled trigger item with a skeleton (role `status`, as today). Error: render
nothing (same as today's `null`), so the menu still shows the colour switch.

**Cleanup.** Replace `LocaleSwitcher.tsx` by `LocaleSubmenu.tsx`; drop the `@ark-ui/react/select` import and
`createListCollection` use.

## Files

**Add** — `apps/web/src/components/layout/LocaleSubmenu.tsx`, optional `useLocalesQuery.ts` (+ tests).

**Delete** — `LocaleSwitcher.tsx` and its test once chapter 5 unmounts it (same deferral as chapter 3).

## Red tests

| Test | Asserts |
| --- | --- |
| `LocaleSubmenu · trigger item is labelled with the language key` | Menu item role, name |
| `LocaleSubmenu · opening lists locales from the API` | One item per locale |
| `LocaleSubmenu · marks the active locale as checked` | Checked state on current |
| `LocaleSubmenu · choosing a locale calls setLocale and persists it` | localStorage updated |
| `LocaleSubmenu · shows a skeleton while locales load` | Loading state |
| `LocaleSubmenu · renders nothing when the locales request fails` | Negative |
| `LocaleSubmenu · keyboard: Right arrow opens, Esc closes the submenu` | Keyboard contract |

## Green

1. Submenu with static items, then wire the query and `setLocale`.
2. Loading and error states.

## Refactor gate

One component per file, ≤ ~100 LOC, methods ~5 LOC. Tests must mock `fetch` for `/api/v1/locales`
(the global stub returns 503).

## Verification

Unit tests, gate commands, `./ci.sh`.

## Out of scope

Mounting inside the burger menu (chapter 5); adding languages.

## Git workflow

Branch `feat/floating-nav-language-submenu`; `test(web): describe language submenu`, then
`feat(web): add language submenu`; one PR.
