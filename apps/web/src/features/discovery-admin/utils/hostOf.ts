/** The host of an absolute URL, or an empty string when it is missing or malformed. */
export function hostOf(url: string | null | undefined): string {
  if (!url) return "";
  try {
    return new URL(url).host;
  } catch {
    return "";
  }
}
