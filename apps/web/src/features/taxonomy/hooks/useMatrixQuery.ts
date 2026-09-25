import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchMatrix } from "../services/taxonomyApi";
import type { MatrixResponse } from "../types";
import { TAXONOMY_STALE_TIME_MS } from "./staleTime";

export function useMatrixQuery(municipalityCode: string | null) {
  const { locale } = useLocale();

  return useQuery<MatrixResponse>({
    queryKey: ["matrix", municipalityCode, locale],
    queryFn: () => fetchMatrix({ locale, municipalityCode }),
    staleTime: TAXONOMY_STALE_TIME_MS,
    placeholderData: keepPreviousData,
  });
}
