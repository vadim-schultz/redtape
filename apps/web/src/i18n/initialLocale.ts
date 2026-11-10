import { DEFAULT_LOCALE, isSupportedLocale } from "./localeMeta";

/** The browser language's primary subtag ("ru-RU" gives "ru"). */
function browserLocale(): string {
  return navigator.language.split("-")[0].toLowerCase();
}

/** The stored choice, then the browser language, then `de`; only supported locales count. */
export function initialLocale(): string {
  const candidates = [window.localStorage.getItem("locale"), browserLocale()];
  return candidates.find(isSupportedLocale) ?? DEFAULT_LOCALE;
}

/** `locale` if the API enables it, else `de`; an unknown or empty enabled set changes nothing. */
export function reconcileLocale(
  locale: string,
  enabled: readonly string[] | undefined,
): string {
  if (!enabled?.length || enabled.includes(locale)) return locale;
  return DEFAULT_LOCALE;
}
