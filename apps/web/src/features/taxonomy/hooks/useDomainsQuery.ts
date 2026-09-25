import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchDomains } from "../services/taxonomyApi";
import type { Term } from "../types";
import { TAXONOMY_STALE_TIME_MS } from "./staleTime";

export function useDomainsQuery() {
  const { locale } = useLocale();

  return useQuery<Term[]>({
    queryKey: ["domains", locale],
    queryFn: () => fetchDomains(locale),
    staleTime: TAXONOMY_STALE_TIME_MS,
  });
}
