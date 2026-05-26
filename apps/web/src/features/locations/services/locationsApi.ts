import { apiRequest } from "../../../services/api";

import type { LocationListResponse } from "../types";

export async function fetchStates(
  locale: string,
): Promise<LocationListResponse> {
  return apiRequest<LocationListResponse>("/api/v1/states", {
    method: "GET",
    locale,
    query: { country: "DE" },
  });
}

export async function fetchDistricts(params: {
  locale: string;
  stateCode: string;
}): Promise<LocationListResponse> {
  const { locale, stateCode } = params;

  return apiRequest<LocationListResponse>("/api/v1/districts", {
    method: "GET",
    locale,
    query: { state: stateCode },
  });
}

export async function fetchMunicipalities(params: {
  locale: string;
  districtCode: string;
}): Promise<LocationListResponse> {
  const { locale, districtCode } = params;

  return apiRequest<LocationListResponse>("/api/v1/cities", {
    method: "GET",
    locale,
    query: { district: districtCode },
  });
}
