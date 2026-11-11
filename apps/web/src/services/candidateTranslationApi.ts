import { apiRequest } from "./api";

/** Who made a stored translation: a machine engine, or a person. */
export const TRANSLATION_SOURCES = ["mt", "human"] as const;

export type TranslationSource = (typeof TRANSLATION_SOURCES)[number];

/** That a stored translation exists for the reader's locale, and whether the German original changed since. No text. */
export type TranslationSummary = {
  locale: string;
  source: TranslationSource;
  stale: boolean;
};

/** The stored translated title and description of one candidate. */
export type TranslationText = TranslationSummary & {
  title: string;
  description: string;
  engine: string;
};

/** The stored translation of a candidate in `locale`; a 404 means none is stored. Never a live translation. */
export async function fetchCandidateTranslation(params: {
  id: string;
  locale: string;
}): Promise<TranslationText> {
  const { id, locale } = params;
  return apiRequest<TranslationText>(
    `/api/v1/candidates/${encodeURIComponent(id)}/translation`,
    { locale, query: { locale } },
  );
}
