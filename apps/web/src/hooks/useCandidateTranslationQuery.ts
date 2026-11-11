import { queryKeys } from "../app/queryKeys";
import {
  fetchCandidateTranslation,
  type TranslationText,
} from "../services/candidateTranslationApi";
import { useApiQuery } from "./useApiQuery";

const FIVE_MINUTES_MS = 5 * 60 * 1000;

/** The stored translation of a candidate; idle until `enabled` (the pop-over was opened), then cached for a few minutes. */
export function useCandidateTranslationQuery(
  candidateId: string,
  locale: string,
  enabled: boolean,
) {
  return useApiQuery<TranslationText>(
    queryKeys.candidates.translation(candidateId, locale),
    () => fetchCandidateTranslation({ id: candidateId, locale }),
    { enabled, staleTime: FIVE_MINUTES_MS, retry: 1 },
  );
}
