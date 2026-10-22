import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchLifeSituations } from "../services/taxonomyApi";
import type { Term } from "../types";
import { TAXONOMY_STALE_TIME_MS } from "./staleTime";

export function useLifeSituationsQuery() {
  const { locale } = useLocale();

  return useApiQuery<Term[]>(
    queryKeys.taxonomy.lifeSituations(locale),
    () => fetchLifeSituations(locale),
    { staleTime: TAXONOMY_STALE_TIME_MS },
  );
}
