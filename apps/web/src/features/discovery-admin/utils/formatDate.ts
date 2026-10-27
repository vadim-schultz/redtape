/** Calendar date in the locale ("Oct 26, 2026"); an unparseable value gives an empty string. */
export function formatDate(isoDate: string, locale: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date);
}
