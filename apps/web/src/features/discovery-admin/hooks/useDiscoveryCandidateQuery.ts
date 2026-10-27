import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchDiscoveryCandidate } from "../services/discoveryAdminApi";
import type { DiscoveryCandidateDetailResponse } from "../types";

/** Load one document candidate with its mentions. */
export function useDiscoveryCandidateQuery(candidateId: string | undefined) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryCandidateDetailResponse>(
    queryKeys.discoveryAdmin.candidate(candidateId, locale),
    () =>
      fetchDiscoveryCandidate({
        locale,
        accessToken: accessToken!,
        candidateId: candidateId!,
      }),
    { enabled: Boolean(accessToken && candidateId) },
  );
}
