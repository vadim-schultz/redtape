import { queryKeys } from "../../../app/queryKeys";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchMunicipalities } from "../services/locationsApi";
import type { LocationListResponse } from "../types";

export function useMunicipalitiesQuery(params: {
  locale: string;
  districtCode: string;
}) {
  const { locale, districtCode } = params;

  return useApiQuery<LocationListResponse>(
    queryKeys.locations.municipalities(districtCode, locale),
    () => fetchMunicipalities({ locale, districtCode }),
    { enabled: !!districtCode },
  );
}
