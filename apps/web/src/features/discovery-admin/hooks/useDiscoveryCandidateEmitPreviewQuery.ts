import { queryKeys } from "../../../app/queryKeys";
import { fetchCandidateEmitPreview } from "../services/discoveryAdminApi";
import type { CandidateEmitPreview } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** Load what emitting one candidate would do. */
export function useDiscoveryCandidateEmitPreviewQuery(
  candidateId: string | undefined,
) {
  return useAdminQuery<CandidateEmitPreview>(
    (locale) =>
      queryKeys.discoveryAdmin.candidateEmitPreview(candidateId, locale),
    candidateId
      ? (auth) => fetchCandidateEmitPreview(auth, candidateId)
      : undefined,
  );
}
