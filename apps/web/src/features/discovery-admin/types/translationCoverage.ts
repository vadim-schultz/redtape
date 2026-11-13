/** Card translation counts of one target locale; `stale` is a subset of `translated`. */
export type TranslationLocaleCoverage = {
  locale: string;
  translated: number;
  stale: number;
  pending: number;
  claimed: number;
  failed: number;
};

/** Per target locale, how far the card units are translated, against the candidates that have a German card. */
export type TranslationCoverageResponse = {
  denominator: number;
  locales: TranslationLocaleCoverage[];
};
