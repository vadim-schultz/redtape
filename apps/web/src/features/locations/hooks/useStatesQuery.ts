import { useQuery } from "@tanstack/react-query";

import { fetchStates } from "../services/locationsApi";
import type { LocationListResponse } from "../types";

export function useStatesQuery(locale: string) {
  return useQuery<LocationListResponse>({
    queryKey: ["states", locale],
    enabled: true,
    queryFn: () => fetchStates(locale),
  });
}
