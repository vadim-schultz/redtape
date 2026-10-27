import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { fetchCandidateEmitPreview } from "../services/discoveryAdminApi";
import type { CandidateEmitPreview } from "../types";

/** Load what emitting one candidate would do. */
export function useDiscoveryCandidateEmitPreviewQuery(
  candidateId: string | undefined,
) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<CandidateEmitPreview>(
    queryKeys.discoveryAdmin.candidateEmitPreview(candidateId, locale),
    () =>
      fetchCandidateEmitPreview({
        locale,
        accessToken: accessToken!,
        candidateId: candidateId!,
      }),
    { enabled: Boolean(accessToken && candidateId) },
  );
}
