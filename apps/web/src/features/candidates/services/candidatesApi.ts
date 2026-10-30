import { apiRequest } from "../../../services/api";
import { toListParams } from "../../../services/listQuery";
import type { CandidateListResponse } from "../types";
import type { CandidateListQuery } from "./candidateListQuery";

/** One page of the public, ranked candidate list; needs no session. */
export async function fetchCandidates(params: {
  locale: string;
  query: CandidateListQuery;
}): Promise<CandidateListResponse> {
  const { locale, query } = params;
  return apiRequest<CandidateListResponse>("/api/v1/candidates", {
    locale,
    query: toListParams(query),
  });
}
