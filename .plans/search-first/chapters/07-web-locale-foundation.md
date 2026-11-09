---
name: "Chapter 7 — Web locale foundation"
overview: "Make the web app ready for seven languages: validated locale detection, lang before first paint, plural-aware translation, central formatters, lazy locale bundles, Cyrillic heading fonts, and parity tests across all locales."
id: C7
depends_on:
  - C2
touches:
  - apps/web/src/i18n/
  - apps/web/src/contexts/LocaleContext.tsx
  - apps/web/src/hooks/useRemoteTranslations.ts
  - apps/web/src/utils/
  - apps/web/src/theme/fonts.ts
  - apps/web/src/theme/index.ts
  - apps/web/src/components/layout/menu/LanguageMenuRow.tsx
  - apps/web/src/components/coverage/runGroups.ts
  - apps/web/src/features/discovery-admin/utils/
  - apps/web/index.html
  - apps/web/package.json
execution: chapter-implementer
todos:
  - id: locale-meta
    content: "Add localeMeta as the web's one locale list, tied to the API list by a test, and validate detection against it and the enabled set."
    status: pending
  - id: lang-first-paint
    content: "Set the html lang before first paint and keep it in sync with the active locale."
    status: pending
  - id: plurals
    content: "Add Intl.PluralRules-based plural resolution to t()."
    status: pending
  - id: formatters
    content: "Centralise number, date and relative-time formatting."
    status: pending
  - id: lazy-bundles
    content: "Load non-default locale bundles lazily and remove duplicate-bundle drift."
    status: pending
  - id: fonts
    content: "Give Russian and Ukrainian headings a Cyrillic-capable font and confirm Latin-ext coverage for Turkish, Polish and Romanian."
    status: pending
  - id: parity
    content: "Add global key, placeholder and plural-form parity tests across locale files."
    status: pending
---

# Chapter 7 — Web locale foundation

**Repo:** `redtape` (`apps/web`)
**Depends on:** [Chapter 2](02-backend-locale-foundation.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Fix the web app's locale handling before any new language file exists, so that adding five locales is data, not code. The new search UI (chapters 9 and 10) uses counts and long labels that need plurals and robust fonts.

## Design decisions

- **`src/i18n/localeMeta.ts`** is the web's one locale list: code and the `Intl` tag for each of `de en tr ru uk pl ro`. A test compares its codes with the API's `SUPPORTED_LOCALES` through the existing cross-package read pattern used by `fallback.test.ts` (it already reads the API seed directory).
- **Detection** (`initialLocale.ts`): stored value, then `navigator.language` primary subtag, then `de`; accepted only if it is in `localeMeta`. The dead `?? "de"` is removed. After `useLocalesQuery` resolves, `LocaleContext` reconciles with the **enabled** set: a stored locale that is not enabled falls back to `de` and the stored value is corrected.
- **`lang` before first paint:** a small inline script in `index.html` sets `document.documentElement.lang` from the stored locale (validated against a short literal list); `LocaleContext` keeps it in sync afterwards. `index.html`'s static `lang="en"` becomes `de`, the API default.
- **Plurals:** `t(key, { count })` first looks up `${key}_${Intl.PluralRules(tag).select(count)}`, then `${key}_other`, then `key`. The categories a locale needs are derived from `Intl.PluralRules(tag).resolvedOptions().pluralCategories`, never hardcoded. `{name}` interpolation is unchanged. Guidance in the file header: no nouns interpolated into sentences (Slavic case).
- **Formatters:** one module under `src/utils/format/` (`formatNumber`, `formatDate`, `formatRelativeTime`) taking the active locale from `localeMeta`; replace the ad hoc `Intl` uses in `utils/relativeTime.ts`, `features/discovery-admin/utils/formatNumber.ts` and `formatDate.ts`, and `components/coverage/runGroups.ts`. Move before change: moves and renames in a separate commit from logic.
- **Lazy bundles:** `de` and `en` stay bundled (default and last-resort fallback); every other locale file loads by dynamic `import()` through `loadBundle(locale)` in `i18n/index.ts`, so Vite code-splits them. The remote `/translations` override stays as is.
- **Fonts** (`theme/fonts.ts`, `theme/index.ts`): Space Grotesk, the heading font, has no Cyrillic. Add a Cyrillic-capable heading fallback in the font stack (Inter already covers Cyrillic via `@fontsource` unicode-range subsets; pick a display face with Cyrillic only if the design needs it). Verify the Latin-ext subset is delivered for tr, pl and ro in all three families.
- **Parity tests** (`fallback.test.ts` or split files): every locale file has an identical key set to `en`; each key has the identical set of `{placeholder}` names; each plural family has every category the locale needs. The test runs over whatever locale files exist, so it passes with `de` and `en` now and enforces completeness when chapter 11 adds files.
- Files stay under about 100 lines, components under about 3 props, and imports follow `container → components/hooks → services → types/utils` (`architecture.test.ts`).

## Files

| Path | Change |
| --- | --- |
| `apps/web/src/i18n/localeMeta.ts` | Locale list and `Intl` tags. |
| `apps/web/src/i18n/initialLocale.ts` | Validated detection. |
| `apps/web/src/i18n/index.ts`, `fallback/index.ts` | `loadBundle`, lazy imports, eager `de`/`en`. |
| `apps/web/src/i18n/plural.ts` | Plural key resolution. |
| `apps/web/src/contexts/LocaleContext.tsx` | Reconcile with enabled locales, `lang` sync, plural-aware `t`. |
| `apps/web/index.html` | Inline `lang` script. |
| `apps/web/src/utils/format/` | Central formatters. |
| `apps/web/src/utils/relativeTime.ts`, `features/discovery-admin/utils/formatNumber.ts`, `formatDate.ts`, `components/coverage/runGroups.ts` | Use the formatters. |
| `apps/web/src/theme/fonts.ts`, `theme/index.ts` | Cyrillic heading fallback. |
| `apps/web/src/i18n/fallback/fallback.test.ts` | Global parity tests. |
| `apps/web/src/contexts/LocaleContext.test.tsx`, `i18n/initialLocale.test.ts`, `i18n/plural.test.ts`, `utils/format/*.test.ts` | New tests. |

## Red tests

### Happy path

- `initialLocale · accepts a supported browser language and a stored locale` and ignores `fr`.
- `t · picks plural forms per locale` asserts `one/few/many/other` for `ru`, `one/few/many/other` for `pl`, `one/few/other` for `ro`, `one/other` for `tr` and `en`, using the same key family.
- `LocaleContext · sets lang on change` and the inline script sets it before React mounts (jsdom test of the script function).
- `formatters · format numbers and dates per locale` asserts a Russian and a German number string.
- `parity · locale files share key sets, placeholders and required plural forms`.

### Negative path

- `initialLocale · a stored but disabled locale falls back to de and corrects storage`.
- `t · a missing plural form falls back to _other, then the key` and never throws.
- `parity · fails with a message naming the key and locale` (negative fixture).
- `localeMeta · differs from the API's supported list` fails (guards drift).
- `bundles · an unknown locale loads the en fallback without a network error`.

## Green

1. Moves and renames first (formatters and bundle loading), then logic changes.
2. Detection, `lang`, plurals, then parity tests.
3. Fonts last, checked in a browser at `de` and with a forced `ru` locale.

## Refactor gate

- One locale list on the web; no hardcoded `"de" | "en"` unions left (`grep` for the literals).
- `t` has no branching beyond the documented lookup order; plural logic lives in `plural.ts`.
- No inline `queryKey` literals; no component imports a feature `services/*` module.
- Barrel rules respected; formatter modules are pure and tested.

## Verification

```bash
cd apps/web
npm test -- src/i18n src/contexts/LocaleContext.test.tsx src/utils
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Record bundle sizes before and after lazy loading and the parity coverage in [../run-ledger.md](../run-ledger.md).

## Out of scope

Adding locale files (chapter 11), the language switcher redesign, right-to-left layout, translating documents.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/web-locale-foundation
```

```text
refactor(web): centralise formatters and lazy-load locale bundles
test(web): describe plural lookup, detection and locale parity
feat(web): validate locale detection, set lang early, support plurals
```
