import { apiRequest } from "../../../services/api";

import type { MatrixResponse, Term } from "../types";

export async function fetchDomains(locale: string): Promise<Term[]> {
  return apiRequest<Term[]>("/api/v1/domains", { method: "GET", locale });
}

export async function fetchLifeSituations(locale: string): Promise<Term[]> {
  return apiRequest<Term[]>("/api/v1/life-situations", {
    method: "GET",
    locale,
  });
}

export async function fetchMatrix(params: {
  locale: string;
  municipalityCode: string | null;
}): Promise<MatrixResponse> {
  const { locale, municipalityCode } = params;

  return apiRequest<MatrixResponse>("/api/v1/matrix", {
    method: "GET",
    locale,
    query: municipalityCode
      ? { municipality_code: municipalityCode }
      : undefined,
  });
}
