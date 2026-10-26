/** Title in the active locale, else English, German, any other, or empty. */
export function localizedTitle(
  titleI18n: Record<string, string>,
  locale: string,
): string {
  return (
    titleI18n[locale] ??
    titleI18n.en ??
    titleI18n.de ??
    Object.values(titleI18n)[0] ??
    ""
  );
}
