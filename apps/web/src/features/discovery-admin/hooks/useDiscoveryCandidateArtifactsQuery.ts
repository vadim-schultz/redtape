import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { listCandidateArtifacts } from "../services/discoveryAdminApi";
import type { DiscoveryArtifactListResponse } from "../types";
import { ARTIFACT_STALE_MS } from "./useDiscoveryArtifactsQuery";

/** Load the evidence behind one candidate, refreshing its presigned URLs once stale. */
export function useDiscoveryCandidateArtifactsQuery(
  candidateId: string | undefined,
) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryArtifactListResponse>(
    queryKeys.discoveryAdmin.candidateArtifacts(candidateId, locale),
    () =>
      listCandidateArtifacts({
        locale,
        accessToken: accessToken!,
        candidateId: candidateId!,
      }),
    {
      enabled: Boolean(accessToken && candidateId),
      staleTime: ARTIFACT_STALE_MS,
      refetchOnWindowFocus: true,
    },
  );
}
