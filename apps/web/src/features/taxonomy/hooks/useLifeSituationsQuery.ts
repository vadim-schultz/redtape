import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchLifeSituations } from "../services/taxonomyApi";
import type { Term } from "../types";
import { TAXONOMY_STALE_TIME_MS } from "./staleTime";

export function useLifeSituationsQuery() {
  const { locale } = useLocale();

  return useQuery<Term[]>({
    queryKey: ["life-situations", locale],
    queryFn: () => fetchLifeSituations(locale),
    staleTime: TAXONOMY_STALE_TIME_MS,
  });
}
