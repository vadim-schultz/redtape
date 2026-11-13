import { DEFAULT_LOCALE } from "../i18n/localeMeta";
import { apiRequest } from "./api";

export type LocaleRow = {
  code: string;
  name_native: string;
  name_english: string;
  flag_emoji: string | null;
  enabled: boolean;
  completeness_pct: number;
  /** True when the strings were machine translated and accepted by an operator (never a tool). */
  machine_translated: boolean;
};

/** The supported locales with their `enabled` flag; public, so it needs no sign-in or reader locale. */
export function fetchLocales(): Promise<LocaleRow[]> {
  return apiRequest<LocaleRow[]>("/api/v1/locales", {
    locale: DEFAULT_LOCALE,
  });
}
