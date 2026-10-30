import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import type { CandidateListQuery } from "../services/candidateListQuery";
import { fetchCandidates } from "../services/candidatesApi";
import type { CandidateListResponse } from "../types";

/** One page of the public candidate list; the previous page stays while the next loads. */
export function useCandidatesQuery(query: CandidateListQuery) {
  const { locale } = useLocale();

  return useApiQuery<CandidateListResponse>(
    queryKeys.candidates.list(query, locale),
    () => fetchCandidates({ locale, query }),
    { placeholderData: keepPreviousData },
  );
}
