import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchCandidateEdges } from "../services/discoveryAdminApi";
import type { DiscoveryCandidateEdgesResponse } from "../types";

/** Load the staged edges of one candidate, both the ones it requires and the ones that require it. */
export function useCandidateEdgesQuery(candidateId: string | undefined) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<DiscoveryCandidateEdgesResponse>(
    queryKeys.discoveryAdmin.candidateEdges(candidateId, locale),
    () =>
      fetchCandidateEdges({
        locale,
        accessToken: accessToken!,
        candidateId: candidateId!,
      }),
    { enabled: Boolean(accessToken && candidateId) },
  );
}
