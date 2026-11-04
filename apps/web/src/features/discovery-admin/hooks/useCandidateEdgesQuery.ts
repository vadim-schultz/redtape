import { queryOptions, skipToken } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import {
  fetchCandidateEdges,
  type AdminAuth,
} from "../services/discoveryAdminApi";
import type { DiscoveryCandidateEdgesResponse } from "../types";
import { useAdminQueryFromOptions } from "./useAdminQuery";

/** Build the staged-edge query for one candidate. */
export function candidateEdgesQueryOptions(
  auth: AdminAuth,
  candidateId: string | undefined,
) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.candidateEdges(candidateId, auth.locale),
    queryFn: candidateId
      ? () => fetchCandidateEdges(auth, candidateId)
      : skipToken,
  });
}

/** Load the staged edges of one candidate, both the ones it requires and the ones that require it. */
export function useCandidateEdgesQuery(candidateId: string | undefined) {
  return useAdminQueryFromOptions<DiscoveryCandidateEdgesResponse>((auth) =>
    candidateEdgesQueryOptions(auth, candidateId),
  );
}
