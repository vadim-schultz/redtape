---
name: "Chapter 15 — Language menu flags and machine note"
overview: "Each locale in the language switcher shows its flag beside a visible two-letter code, because emoji flags do not render on Windows. Locales made from machine-accepted strings also show a short 'machine translated' note. The row gets its first unit tests."
id: AZ15
depends_on:
  - AZ14
touches:
  - apps/web/src/components/layout/menu/LanguageMenuRow.tsx
  - apps/web/src/components/layout/menu/LanguageMenuRow.test.tsx
  - apps/web/src/components/layout/menu/LocaleButton.tsx
  - apps/web/src/components/layout/menu/LocaleLabel.tsx
  - apps/web/src/components/layout/menu/MachineNote.tsx
  - apps/web/src/i18n/fallback/
  - apps/api/scripts/seed_data/translations/
execution: chapter-implementer
---

# Chapter 15 — Language menu flags and machine note

**Repo:** `redtape` (`apps/web`, seed data) · **Depends on:** [Chapter 14](14-locale-machine-accepted.md) · **Decisions:** [D4](../gaps-and-decisions.md#d4--interface-locales-are-enabled-on-machine-output) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

The language switcher is readable on every platform, and a machine-translated locale is labelled as such. The flag is kept; the code is added beside it.

## Scope

- In: the row's label, the machine note, unit tests for the row (it has none of its own today), keys in seven locales.
- Out: the manifest and the enable gate (14), the locale list's source (unchanged).

## Design

1. **Current state.** `LanguageMenuRow.tsx` renders `{entry.flag_emoji}` in an icon button with `aria-label={name_native}` and `aria-pressed`. Flags come from the API. The row has no unit test of its own.
2. **Label.** `LocaleLabel` renders the flag emoji and the uppercase code (`entry.code`, for example `TR`) as visible text. The accessible name stays the native name, so screen readers do not read the code.
3. **Machine note.** `MachineNote` renders when `machine_translated` is true. Its text comes from a key (`menu.machine_translated_note`) in all seven locales, and falls back to English when the key is missing.
4. **Button.** `LocaleButton` keeps `aria-pressed` for the current locale and the existing 44 px target.
5. **Split.** `LanguageMenuRow` composes the three parts. Each part is one file.
6. **Missing flag.** A locale without `flag_emoji` shows the code only, with no crash.

## Files

| Path | Change |
| --- | --- |
| `components/layout/menu/LanguageMenuRow.tsx` | composes the parts |
| `components/layout/menu/LocaleButton.tsx`, `LocaleLabel.tsx`, `MachineNote.tsx` (new) | parts, one per file |
| `components/layout/menu/LanguageMenuRow.test.tsx` (new) | row tests |
| `i18n/fallback/*.json`, `apps/api/scripts/seed_data/translations/*.json` | `menu.machine_translated_note` in seven locales |

## Red tests

**Happy path**
- `Row · each enabled locale shows its flag and its uppercase code`
- `Row · a machine_translated locale shows the note; a reviewed locale does not`
- `Row · the accessible name is the native name, not the code`
- `Row · selecting a locale calls setLocale, and the current one has aria-pressed`
- `Row · the button is at least 44 px high`

**Negative path**
- `Row · a locale without flag_emoji shows the code only and does not crash`
- `Row · a missing note key falls back to English`

## Green

Start with the accessible name, since it is the constraint most likely to be broken by the new code, then the label, the note and the split.

## Refactor gate

- Three parts, each about 40 lines or fewer, with at most 3 props.
- No boolean prop for the note; pass the locale entry.
- House rules: one component per file, no inline styles beyond the theme tokens, no physical properties where logical ones exist.

## Verification

```bash
cd apps/web
npm test -- LanguageMenuRow LocaleContext AppMenu fallback parity
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

## Out of scope

The enable gate and manifest (14), flags as images, right-to-left layout.

## Operator steps after merge

None.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-15-language-menu
# test(web): ... (red), feat(web): ... (green), refactor(web): ... (gate), feat(api): seed key
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
