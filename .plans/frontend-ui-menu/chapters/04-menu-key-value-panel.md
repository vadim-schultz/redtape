---
name: "Chapter 4 — Menu key–value panel"
overview: "Rebuild AppMenu body as four KeyValueRow rows: Profile, Documents, colour switch, language flags."
todos:
  - id: panel
    content: "AppMenuPanel + row components"
    status: pending
  - id: i18n
    content: "menu.profile, menu.colour_mode in en/de (+ seed if required)"
    status: pending
  - id: cleanup
    content: "Remove AccountMenuItem, SuggestMenuItem, LocaleSubmenu if unused"
    status: pending
isProject: false
---

# Chapter 4 — Menu key–value panel

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/frontend-ui-menu-kv-panel` · **Status:** planned

**Depends on:** [3](03-key-value-row.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §2–3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-frontend-ui-menu` · **Release branch:** `main`

---

## Goal

Replace vertical `Menu.Item` list with `AppMenuPanel`: four `KeyValueRow` rows per architecture. Profile uses
`FaEnvelope`, `FaGoogle`, `FaRegUser` from `react-icons/fa`.

## Design decisions

**Profile.** Anonymous: envelope + Google → `/login`. Authenticated: `FaRegUser` + sign-out. Unconfigured: omit row (D7).

**Documents.** Label + value column with links to `/documents` and `/suggest`.

**Colour.** Wrap existing `ColorModeSwitch`; menu stays open on toggle.

**Language.** Ghost flag buttons; selected state highlighted; close menu on locale change (mirror prior submenu test).

**Structure.** Suggested files under `components/layout/menu/`: `AppMenuPanel.tsx`, `ProfileMenuRow.tsx`,
`DocumentsMenuRow.tsx`, `ColorModeMenuRow.tsx`, `LanguageMenuRow.tsx`.

## Files

**Add** — `components/layout/menu/*.tsx` (+ tests as needed).

**Edit** — `AppMenu.tsx`, `AppMenu.test.tsx`, `i18n/fallback/{en,de}.json`, API seed if parity test exists.

**Delete** — `AccountMenuItem`, `SuggestMenuItem`, `LocaleSubmenu` when fully replaced.

## Red tests

| Test | Asserts |
| --- | --- |
| `AppMenu · opens panel with four key-value rows` | Four `data-testid="key-value-row"` with expected labels |
| `AppMenu · toggling the colour switch keeps the menu open` | Preserved |
| `AppMenu · choosing a language via flag updates locale and closes menu` | Inline buttons |
| `AppMenu · anonymous profile row shows envelope and google not user icon` | Negative path |
| `AppMenu · authenticated profile row shows user icon` | Happy path with fake gateway |
| `AppMenu · language row absent when locales request fails` | Negative path |

## Green

Wire panel; remove obsolete menu items; i18n keys.

## Refactor gate

`AppMenu` + panel rows; auth state dispatch if >2 paths; report outcome.

## Verification

```bash
cd apps/web
npm run test -- src/components/layout/AppMenu.test.tsx src/components/layout/menu
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Manual smoke per [01-rollout.md](../01-rollout.md).

## Git workflow

```bash
git checkout feat/plans-frontend-ui-menu && git pull
git checkout -b feat/frontend-ui-menu-kv-panel
```

```text
test(web): menu panel key-value rows and profile icons

feat(web): rebuild app menu as KeyValueRow panel
```

Open PR **into `feat/plans-frontend-ui-menu`**.

After all chapters merge to the loop branch, chief of staff opens **one release PR** `feat/plans-frontend-ui-menu` → `main`.
