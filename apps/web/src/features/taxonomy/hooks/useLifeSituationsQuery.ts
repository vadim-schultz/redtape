import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchLifeSituations } from "../services/taxonomyApi";
import type { GroupedTerm } from "../types";
import { TAXONOMY_STALE_TIME_MS } from "../utils/staleTime";

export function useLifeSituationsQuery() {
  const { locale } = useLocale();

  return useApiQuery<GroupedTerm[]>(
    queryKeys.taxonomy.lifeSituations(locale),
    () => fetchLifeSituations(locale),
    { staleTime: TAXONOMY_STALE_TIME_MS },
  );
}
