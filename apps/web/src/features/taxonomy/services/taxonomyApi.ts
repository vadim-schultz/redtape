import { apiRequest } from "../../../services/api";

import type { Term } from "../types";

export async function fetchDomains(locale: string): Promise<Term[]> {
  return apiRequest<Term[]>("/api/v1/domains", { method: "GET", locale });
}

export async function fetchLifeSituations(locale: string): Promise<Term[]> {
  return apiRequest<Term[]>("/api/v1/life-situations", {
    method: "GET",
    locale,
  });
}
