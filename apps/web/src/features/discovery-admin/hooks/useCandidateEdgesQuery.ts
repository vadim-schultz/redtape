import { queryKeys } from "../../../app/queryKeys";
import { fetchCandidateEdges } from "../services/discoveryAdminApi";
import type { DiscoveryCandidateEdgesResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load the staged edges of one candidate, both the ones it requires and the ones that require it. */
export function useCandidateEdgesQuery(candidateId: string | undefined) {
  return useAdminQuery<DiscoveryCandidateEdgesResponse>(
    (locale) => queryKeys.discoveryAdmin.candidateEdges(candidateId, locale),
    candidateId ? (auth) => fetchCandidateEdges(auth, candidateId) : undefined,
  );
}
