import { apiRequest } from "../../../services/api";
import type { SuggestionListResponse, SuggestionRead } from "../types";

export async function fetchSuggestions(params: {
  locale: string;
  status?: string[];
  kind?: string;
  jurisdictionId?: string;
}): Promise<SuggestionListResponse> {
  const { locale, status, kind, jurisdictionId } = params;

  return apiRequest<SuggestionListResponse>("/api/v1/suggestions", {
    method: "GET",
    locale,
    query: {
      status,
      kind,
      jurisdiction_id: jurisdictionId,
    },
  });
}

export async function fetchSuggestionDetail(params: {
  locale: string;
  id: string;
}): Promise<SuggestionRead> {
  const { locale, id } = params;

  return apiRequest<SuggestionRead>(`/api/v1/suggestions/${id}`, {
    locale,
    method: "GET",
  });
}
