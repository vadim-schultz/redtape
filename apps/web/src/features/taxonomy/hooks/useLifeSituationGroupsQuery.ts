import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchLifeSituationGroups } from "../services/taxonomyApi";
import type { Term } from "../types";
import { TAXONOMY_STALE_TIME_MS } from "../utils/staleTime";

export function useLifeSituationGroupsQuery() {
  const { locale } = useLocale();

  return useApiQuery<Term[]>(
    queryKeys.taxonomy.lifeSituationGroups(locale),
    () => fetchLifeSituationGroups(locale),
    { staleTime: TAXONOMY_STALE_TIME_MS },
  );
}
