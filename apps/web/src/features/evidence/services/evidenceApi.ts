import { apiRequest } from "../../../services/api";
import type { EvidenceListResponse } from "../types";

export async function fetchEvidenceForSuggestion(
  suggestionId: string,
  locale: string,
): Promise<EvidenceListResponse> {
  return apiRequest<EvidenceListResponse>(
    `/api/v1/suggestions/${suggestionId}/evidence`,
    { locale },
  );
}
