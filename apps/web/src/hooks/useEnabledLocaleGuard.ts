import { useEffect } from "react";

import { reconcileLocale } from "../i18n/initialLocale";
import { useLocalesQuery } from "./useLocalesQuery";

/** Codes of enabled locales; undefined unless the response is a list. */
function enabledCodes(rows: unknown): string[] | undefined {
  if (!Array.isArray(rows)) return undefined;
  return rows.filter((row) => row?.enabled).map((row) => row.code);
}

/** Once the locale list arrives, swap a locale that is not enabled for `de` (setLocale corrects storage). */
export function useEnabledLocaleGuard(
  locale: string,
  setLocale: (next: string) => void,
): void {
  const { data } = useLocalesQuery();

  useEffect(() => {
    const next = reconcileLocale(locale, enabledCodes(data));
    if (next !== locale) setLocale(next);
  }, [data, locale, setLocale]);
}
