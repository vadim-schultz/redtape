import { buildApiUrl } from "../../../services/apiOrigin";
import { apiRequest } from "../../../services/api";
import { toListParams } from "../../../services/listQuery";
import type { CandidateDetail, CandidateListResponse } from "../types";
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

/** One candidate with its neighbours and evidence; a 404 means no such candidate. */
export async function fetchCandidate(params: {
  locale: string;
  id: string;
}): Promise<CandidateDetail> {
  const { locale, id } = params;
  return apiRequest<CandidateDetail>(
    `/api/v1/candidates/${encodeURIComponent(id)}`,
    { locale },
  );
}

/** Where the browser loads a candidate's screenshot from: the public proxy route. */
export function candidateScreenshotUrl(id: string): string {
  return buildApiUrl(
    `/api/v1/candidates/${encodeURIComponent(id)}/screenshot`,
  ).toString();
}
