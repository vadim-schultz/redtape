---
name: Chapter C2 - Flag-only language menu
overview: "The language row of the app menu shows one flag button per enabled locale, with no code and no machine-translation note."
id: C2
depends_on: []
touches:
  - apps/web/src/components/layout/menu/
  - apps/web/src/i18n/fallback/
  - apps/api/scripts/seed_data/translations/
execution: chapter-implementer
isProject: false
---

# C2 - Flag-only language menu

**Depends on:** none · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [01-rollout.md](../01-rollout.md)

## Goal

After C2, the language row of the app menu shows one flag button for each enabled locale. The accessible name of each button is the native language name. The row shows no locale code and no "Machine translated" note.

## Read first

- [00-architecture.md](../00-architecture.md): invariant I7, and the language menu row of the current surface.
- [gaps-and-decisions.md](../gaps-and-decisions.md): D8 and D9.
- [01-rollout.md](../01-rollout.md): the per-chapter gate.

## Coordination scope

**Add:**

- None.

**Edit:**

- `apps/web/src/components/layout/menu/LanguageMenuRow.tsx`: drops the per-locale stack and the note.
- `apps/web/src/components/layout/menu/LanguageMenuRow.test.tsx`: the tests of this chapter.
- `apps/web/src/components/layout/menu/LocaleLabel.tsx`: shows the flag only, or the native name when a locale has no flag.
- `apps/web/src/components/layout/menu/LocaleButton.tsx`: keeps the native name as its accessible name. Change nothing else.
- `apps/web/src/i18n/fallback/*.json`: removes the key `menu.machine_translated_note`.
- `apps/api/scripts/seed_data/translations/*.json`: removes the same key from each seed file.

**Delete:**

- `apps/web/src/components/layout/menu/MachineNote.tsx`. No import remains after the edit.

**Do not edit:**

- `apps/web/src/services/localesApi.ts`: the `machine_translated` field stays (D9).
- `apps/api/app/`: the locales API keeps its responses (I3).
- Other components that use machine-translation notes, such as `TranslationPopover`. They show the status of a content translation, not the menu.

## Work items

1. **Flags only, with the native name as accessible name.**
   - **Red, happy path:** `renders_each_enabled_locale_as_flag_button_named_by_native_name`. Two enabled locales produce two buttons. Each button's accessible name is its `name_native`, and its visible text is the flag emoji.
   - **Red, negative path:** `shows_no_locale_code_and_no_machine_note`. For a machine-translated locale, the text of its code (for example `DE`) and the text "Machine translated" are both absent.
   - **Green:** `LocaleLabel` renders the flag. A locale without a flag renders its native name as text (D8). `LanguageMenuRow` removes the per-locale `VStack` and renders `MachineNote` nowhere.
   - **Refactor candidates:** `LocaleLabel` has two arms, the flag and the native name. Two arms are allowed. `LanguageMenuRow` keeps its loading arm and its error arm. Delete `MachineNote.tsx`, because no import remains.

2. **Remove the machine-translation string.**
   - **Red:** item 1's negative test fails while the note still renders. No separate test is needed.
   - **Green:** remove `menu.machine_translated_note` from every `apps/web/src/i18n/fallback/*.json` file and from every `apps/api/scripts/seed_data/translations/*.json` file. Keep the other `menu.*` keys.
   - **Refactor candidates:** none. The removal changes data only.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Language row | `renders_each_enabled_locale_as_flag_button_named_by_native_name` | `shows_no_locale_code_and_no_machine_note` |
| String removal | The i18n tests pass with the key removed | `grep` finds no `machine_translated_note` in the web source or the seed data |

## Review gate

- Each test was red before the green change.
- Every button keeps a native-name accessible name. Query the buttons by role and name in the tests.
- No file outside the touches list changed.
- `MachineNote.tsx` is gone, and no import of it remains.

## Out of scope

- The `machine_translated` field in the API and its type (D9).
- The Language label of the row. It stays, because the row keeps its key-value layout.
- Any other menu row. The Documents row changes in C5.

## Verification

```bash
# Run from the repository root.
cd apps/web
npx vitest run src/components/layout/menu src/i18n
npm run lint
npm run typecheck
cd ../..
grep -rn "machine_translated_note" apps/web/src apps/api/scripts || echo "no matches"
```

Expected: `vitest` exits 0. `lint` and `typecheck` exit 0. The `grep` prints no match, and the script prints `no matches`.

## Refactor report

_Pending. The implementer fills this in after the refactor pass. It must name each candidate and state its outcome._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`.
- Create the chapter branch with `git checkout -b feat/discovery-admin-flow-c2-language-flags`.
- Commit the red tests first, as `test(menu): ...`. Then commit the green change, as `feat(menu): ...`. Then commit the refactor, as `refactor(menu): ...`.
- Run the local gate on the chapter branch with `./ci.sh all`. It passes when it exits 0.
- Do not push, and do not open a pull request. Remote CI runs once, on the release pull request.
- The chief merges the chapter branch into the loop branch locally, with `git merge --no-ff`.
