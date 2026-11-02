import { queryKeys } from "../../../app/queryKeys";
import { listCandidateArtifacts } from "../services/discoveryAdminApi";
import type { DiscoveryArtifactListResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";
import { ARTIFACT_STALE_MS } from "./useDiscoveryArtifactsQuery";

/** Load the evidence behind one candidate, refreshing its presigned URLs once stale. */
export function useDiscoveryCandidateArtifactsQuery(
  candidateId: string | undefined,
) {
  return useAdminQuery<DiscoveryArtifactListResponse>(
    (locale) =>
      queryKeys.discoveryAdmin.candidateArtifacts(candidateId, locale),
    candidateId
      ? (auth) => listCandidateArtifacts(auth, candidateId)
      : undefined,
    { staleTime: ARTIFACT_STALE_MS, refetchOnWindowFocus: true },
  );
}
