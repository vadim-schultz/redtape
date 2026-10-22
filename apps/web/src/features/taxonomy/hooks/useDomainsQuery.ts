import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchDomains } from "../services/taxonomyApi";
import type { Term } from "../types";
import { TAXONOMY_STALE_TIME_MS } from "./staleTime";

export function useDomainsQuery() {
  const { locale } = useLocale();

  return useApiQuery<Term[]>(
    queryKeys.taxonomy.domains(locale),
    () => fetchDomains(locale),
    { staleTime: TAXONOMY_STALE_TIME_MS },
  );
}
