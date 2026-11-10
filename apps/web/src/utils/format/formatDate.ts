import { intlTag } from "../../i18n/localeMeta";

function parse(isoDate: string): Date | null {
  const date = new Date(isoDate);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Calendar date in the locale ("Oct 26, 2026"); an unparseable value gives an empty string. */
export function formatDate(isoDate: string, locale: string): string {
  const date = parse(isoDate);
  if (!date) return "";
  return new Intl.DateTimeFormat(intlTag(locale), {
    dateStyle: "medium",
  }).format(date);
}

/** Date and time in the locale; `timeZone` defaults to the browser's. Unparseable gives an empty string. */
export function formatDateTime(
  isoDate: string,
  locale: string,
  timeZone?: string,
): string {
  const date = parse(isoDate);
  if (!date) return "";
  return new Intl.DateTimeFormat(intlTag(locale), {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone,
  }).format(date);
}
