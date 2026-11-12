import { queryKeys } from "../app/queryKeys";
import {
  fetchDocumentTranslation,
  type DocumentTranslationAnswer,
} from "../services/documentTranslationApi";
import { useApiQuery } from "./useApiQuery";

const FIVE_MINUTES_MS = 5 * 60 * 1000;

/** The translated page of a candidate in `locale`; idle until `enabled` (the item was opened), then cached for a few minutes. */
export function useDocumentTranslationQuery(
  candidateId: string,
  locale: string,
  enabled: boolean,
) {
  return useApiQuery<DocumentTranslationAnswer>(
    queryKeys.candidates.documentTranslation(candidateId, locale),
    () => fetchDocumentTranslation({ id: candidateId, locale }),
    { enabled, staleTime: FIVE_MINUTES_MS },
  );
}
