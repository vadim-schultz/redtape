import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchCandidate } from "../services/candidatesApi";
import type { CandidateDetail } from "../types";

/** One candidate's detail; idle until the route supplies an id. */
export function useCandidateDetailQuery(id: string | undefined) {
  const { locale } = useLocale();

  return useApiQuery<CandidateDetail>(
    queryKeys.candidates.detail(id, locale),
    () => fetchCandidate({ locale, id: id as string }),
    { enabled: !!id },
  );
}
