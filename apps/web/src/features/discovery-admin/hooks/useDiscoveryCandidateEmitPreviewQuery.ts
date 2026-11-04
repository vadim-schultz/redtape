import { queryOptions, skipToken } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import {
  fetchCandidateEmitPreview,
  type AdminAuth,
} from "../services/discoveryAdminApi";
import { useAdminQueryFromOptions } from "./useAdminQuery";

/** Build the emit-preview query for one candidate. */
export function candidateEmitPreviewQueryOptions(
  auth: AdminAuth,
  candidateId: string | undefined,
) {
  return queryOptions({
    queryKey: queryKeys.discoveryAdmin.candidateEmitPreview(
      candidateId,
      auth.locale,
    ),
    queryFn: candidateId
      ? () => fetchCandidateEmitPreview(auth, candidateId)
      : skipToken,
  });
}

/** Load what emitting one candidate would do. */
export function useDiscoveryCandidateEmitPreviewQuery(
  candidateId: string | undefined,
) {
  return useAdminQueryFromOptions((auth) =>
    candidateEmitPreviewQueryOptions(auth, candidateId),
  );
}
