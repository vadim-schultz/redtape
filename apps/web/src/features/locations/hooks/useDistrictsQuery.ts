import { useQuery } from '@tanstack/react-query';

import { fetchDistricts } from '../services/locationsApi';
import type { LocationListResponse } from '../types';

export function useDistrictsQuery(params: { locale: string; stateCode: string }) {
  const { locale, stateCode } = params;

  return useQuery<LocationListResponse>({
    queryKey: ['districts', stateCode, locale],
    enabled: !!stateCode,
    queryFn: () => fetchDistricts({ locale, stateCode }),
  });
}

