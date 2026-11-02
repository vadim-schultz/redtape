import { queryKeys } from "../../../app/queryKeys";
import { fetchDiscoveryCandidate } from "../services/discoveryAdminApi";
import type { DiscoveryCandidateDetailResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load one document candidate with its mentions. */
export function useDiscoveryCandidateQuery(candidateId: string | undefined) {
  return useAdminQuery<DiscoveryCandidateDetailResponse>(
    (locale) => queryKeys.discoveryAdmin.candidate(candidateId, locale),
    candidateId
      ? (auth) => fetchDiscoveryCandidate(auth, candidateId)
      : undefined,
  );
}
