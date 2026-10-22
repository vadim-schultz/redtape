import { queryKeys } from "../../../app/queryKeys";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchDistricts } from "../services/locationsApi";
import type { LocationListResponse } from "../types";

export function useDistrictsQuery(params: {
  locale: string;
  stateCode: string;
}) {
  const { locale, stateCode } = params;

  return useApiQuery<LocationListResponse>(
    queryKeys.locations.districts(stateCode, locale),
    () => fetchDistricts({ locale, stateCode }),
    { enabled: !!stateCode },
  );
}
