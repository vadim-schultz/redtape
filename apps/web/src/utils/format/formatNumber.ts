import { intlTag } from "../../i18n/localeMeta";

/** Number in the locale with at most one decimal ("120.5", "1,5"). */
export function formatNumber(value: number, locale: string): string {
  return new Intl.NumberFormat(intlTag(locale), {
    maximumFractionDigits: 1,
  }).format(value);
}
