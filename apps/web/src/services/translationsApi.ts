import type { TranslationBundle } from "../i18n/fallback";
import { buildApiUrl } from "./apiOrigin";

/** Fetch the remote translation bundle; rejects on a non-OK response. */
export async function fetchTranslations(
  locale: string,
  signal: AbortSignal,
): Promise<TranslationBundle> {
  const url = buildApiUrl("/api/v1/translations");
  url.searchParams.set("locale", locale);
  const res = await fetch(url.toString(), {
    headers: { "Accept-Language": locale },
    signal,
  });
  if (!res.ok) throw new Error(`Translations request failed: ${res.status}`);
  const data = (await res.json()) as { translations?: TranslationBundle };
  return data.translations ?? {};
}
