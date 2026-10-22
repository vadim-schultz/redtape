import { queryKeys } from "../../../app/queryKeys";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchStates } from "../services/locationsApi";
import type { LocationListResponse } from "../types";

export function useStatesQuery(locale: string) {
  return useApiQuery<LocationListResponse>(
    queryKeys.locations.states(locale),
    () => fetchStates(locale),
    { enabled: true },
  );
}
