import { apiRequest } from "../../../services/api";

import type { DocumentDetail, DocumentListResponse } from "../types";

export async function fetchDocuments(params: {
  locale: string;
  municipalityCode: string | null;
  domains: string[];
  situations: string[];
}): Promise<DocumentListResponse> {
  const { locale, municipalityCode, domains, situations } = params;

  return apiRequest<DocumentListResponse>("/api/v1/documents", {
    method: "GET",
    locale,
    query: {
      municipality_code: municipalityCode ?? undefined,
      domain: domains,
      situation: situations,
    },
  });
}

export async function fetchDocumentDetail(params: {
  locale: string;
  id: string;
}): Promise<DocumentDetail> {
  const { locale, id } = params;

  return apiRequest<DocumentDetail>(`/api/v1/documents/${id}`, {
    locale,
    method: "GET",
  });
}
