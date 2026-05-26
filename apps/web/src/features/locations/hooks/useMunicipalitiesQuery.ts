import { useQuery } from "@tanstack/react-query";

import { fetchMunicipalities } from "../services/locationsApi";
import type { LocationListResponse } from "../types";

export function useMunicipalitiesQuery(params: {
  locale: string;
  districtCode: string;
}) {
  const { locale, districtCode } = params;

  return useQuery<LocationListResponse>({
    queryKey: ["municipalities", districtCode, locale],
    enabled: !!districtCode,
    queryFn: () => fetchMunicipalities({ locale, districtCode }),
  });
}
