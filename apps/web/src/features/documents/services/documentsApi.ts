import { apiRequest } from "../../../services/api";

import type { DocumentDetail, DocumentListResponse } from "../types";

export async function fetchDocuments(params: {
  locale: string;
  municipalityCode: string | null;
}): Promise<DocumentListResponse> {
  const { locale, municipalityCode } = params;

  return apiRequest<DocumentListResponse>("/api/v1/documents", {
    method: "GET",
    locale,
    query: municipalityCode
      ? { municipality_code: municipalityCode }
      : undefined,
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
