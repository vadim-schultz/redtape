import { queryOptions, skipToken } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import {
  listCandidateArtifacts,
  type AdminAuth,
} from "../services/discoveryAdminApi";
import { ARTIFACT_STALE_MS } from "../constants/queryTiming";
import { useAdminQueryFromOptions } from "./useAdminQuery";

/** Build the artifact query for one candidate. */
export function candidateArtifactsQueryOptions(
  auth: AdminAuth,
  candidateId: string | undefined,
) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.candidateArtifacts(
      candidateId,
      auth.locale,
    ),
    queryFn: candidateId
      ? () => listCandidateArtifacts(auth, candidateId)
      : skipToken,
    staleTime: ARTIFACT_STALE_MS,
    refetchOnWindowFocus: true,
  });
}

/** Load the evidence behind one candidate, refreshing its presigned URLs once stale. */
export function useDiscoveryCandidateArtifactsQuery(
  candidateId: string | undefined,
) {
  return useAdminQueryFromOptions((auth) =>
    candidateArtifactsQueryOptions(auth, candidateId),
  );
}
