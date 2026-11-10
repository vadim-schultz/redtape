/**
 * The web's one locale list: each interface language and its `Intl` tag.
 *
 * `localeMeta.test.ts` ties it to `SUPPORTED_LOCALES` in the API. All locales
 * are left to right; a text-direction field would go here.
 */
export const LOCALE_META = [
  { code: "de", tag: "de" },
  { code: "en", tag: "en" },
  { code: "tr", tag: "tr" },
  { code: "ru", tag: "ru" },
  { code: "uk", tag: "uk" },
  { code: "pl", tag: "pl" },
  { code: "ro", tag: "ro" },
] as const;

export type LocaleCode = (typeof LOCALE_META)[number]["code"];

export const LOCALE_CODES: readonly LocaleCode[] = LOCALE_META.map(
  (meta) => meta.code,
);

/** The API default and last-resort locale; the first entry of the list. */
export const DEFAULT_LOCALE: LocaleCode = LOCALE_CODES[0];

/** True when `code` is one of the supported interface locales. */
export function isSupportedLocale(
  code: string | null | undefined,
): code is LocaleCode {
  return LOCALE_CODES.some((known) => known === code);
}

/** The `Intl` tag for `code`; an unknown code gets the default locale's tag. */
export function intlTag(code: string): string {
  const meta = LOCALE_META.find((entry) => entry.code === code);
  return (meta ?? LOCALE_META[0]).tag;
}
